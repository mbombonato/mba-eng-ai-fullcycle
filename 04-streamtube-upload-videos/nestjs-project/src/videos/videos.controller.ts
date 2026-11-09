import {
  Body,
  Controller,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  Post,
  Redirect,
} from '@nestjs/common';
import {
  ApiBearerAuth,
  ApiOperation,
  ApiResponse,
  ApiTags,
  getSchemaPath,
} from '@nestjs/swagger';
import { SkipThrottle } from '@nestjs/throttler';
import type { JwtPayload } from '../auth/auth.types';
import { CurrentUser } from '../auth/decorators/current-user.decorator';
import { Public } from '../auth/decorators/public.decorator';
import { ApiErrorEnvelope } from '../common/openapi/api-error-envelope.dto';
import { CompleteUploadDto } from './dto/complete-upload.dto';
import { CreateVideoResponseDto } from './dto/create-video-response.dto';
import { CreateVideoDto } from './dto/create-video.dto';
import { VideoResponseDto } from './dto/video-response.dto';
import { VideoSlugParamDto } from './dto/video-slug-param.dto';
import { VideosService } from './videos.service';

interface RedirectResponse {
  url: string;
  statusCode: number;
}

const ERROR_SCHEMA = { $ref: getSchemaPath(ApiErrorEnvelope) };
const LOCATION_HEADER = {
  Location: {
    description: 'Short-lived presigned URL on the object storage',
    schema: { type: 'string' },
  },
};

@ApiTags('videos')
@SkipThrottle()
@Controller('videos')
export class VideosController {
  constructor(private readonly videosService: VideosService) {}

  @Post()
  @ApiBearerAuth('access-token')
  @ApiOperation({
    summary: 'Start a video upload',
    description:
      "Pre-registers the video as a draft in the caller's channel and opens a direct-to-storage multipart upload. The response carries one presigned URL per part: PUT each part straight to the storage (the API never receives the file), keep each ETag and call POST /videos/{slug}/upload/complete.",
  })
  @ApiResponse({
    status: 201,
    description: 'Draft created and multipart upload opened',
    type: CreateVideoResponseDto,
  })
  @ApiResponse({
    status: 400,
    description: 'Validation failed',
    schema: ERROR_SCHEMA,
  })
  @ApiResponse({
    status: 401,
    description: 'Missing or invalid access token',
    schema: ERROR_SCHEMA,
  })
  @ApiResponse({
    status: 404,
    description: 'User has no channel',
    schema: ERROR_SCHEMA,
  })
  async create(
    @CurrentUser() user: JwtPayload,
    @Body() dto: CreateVideoDto,
  ): Promise<CreateVideoResponseDto> {
    const session = await this.videosService.createUpload(user.sub, dto);
    return {
      video: VideoResponseDto.fromEntity(session.video),
      upload: {
        upload_id: session.uploadId,
        part_size: session.partSize,
        part_count: session.partCount,
        expires_at: session.expiresAt.toISOString(),
        parts: session.parts.map((p) => ({
          part_number: p.partNumber,
          url: p.url,
        })),
      },
    };
  }

  @Post(':slug/upload/complete')
  @HttpCode(HttpStatus.OK)
  @ApiBearerAuth('access-token')
  @ApiOperation({
    summary: 'Complete a video upload',
    description:
      'Completes the multipart upload with the uploaded parts, verifies the stored size (max 10 GB) and enqueues automatic processing. Status changes from draft to processing.',
  })
  @ApiResponse({
    status: 200,
    description: 'Upload completed, processing enqueued',
    type: VideoResponseDto,
  })
  @ApiResponse({
    status: 400,
    description: 'Validation failed or invalid upload parts',
    schema: ERROR_SCHEMA,
  })
  @ApiResponse({
    status: 401,
    description: 'Missing or invalid access token',
    schema: ERROR_SCHEMA,
  })
  @ApiResponse({
    status: 404,
    description: 'Video not found or caller is not the owner',
    schema: ERROR_SCHEMA,
  })
  @ApiResponse({
    status: 409,
    description: 'Video is not a draft',
    schema: ERROR_SCHEMA,
  })
  @ApiResponse({
    status: 422,
    description: 'Stored file exceeds 10 GB',
    schema: ERROR_SCHEMA,
  })
  async completeUpload(
    @CurrentUser() user: JwtPayload,
    @Param() params: VideoSlugParamDto,
    @Body() dto: CompleteUploadDto,
  ): Promise<VideoResponseDto> {
    const video = await this.videosService.completeUpload(
      user.sub,
      params.slug,
      dto,
    );
    return VideoResponseDto.fromEntity(video);
  }

  @Public()
  @Get(':slug')
  @ApiOperation({
    summary: 'Get a video by its unique URL',
    description:
      'Returns the video identified by its unique slug. Ready videos are public; draft, processing and failed videos are only visible to the owner (send the access token).',
  })
  @ApiResponse({
    status: 200,
    description: 'Video found',
    type: VideoResponseDto,
  })
  @ApiResponse({
    status: 400,
    description: 'Malformed slug',
    schema: ERROR_SCHEMA,
  })
  @ApiResponse({
    status: 404,
    description: 'Video not found',
    schema: ERROR_SCHEMA,
  })
  async findOne(
    @Param() params: VideoSlugParamDto,
    @CurrentUser() user?: JwtPayload,
  ): Promise<VideoResponseDto> {
    const video = await this.videosService.findVisibleBySlug(
      params.slug,
      user?.sub,
    );
    return VideoResponseDto.fromEntity(video);
  }

  @Public()
  @Get(':slug/stream')
  @Redirect()
  @ApiOperation({
    summary: 'Stream a video',
    description:
      'Redirects (302) to a short-lived presigned URL on the object storage, which answers HTTP Range requests with 206 Partial Content — playback starts without downloading the whole file.',
  })
  @ApiResponse({
    status: 302,
    description: 'Redirect to the streamable file',
    headers: LOCATION_HEADER,
  })
  @ApiResponse({
    status: 400,
    description: 'Malformed slug',
    schema: ERROR_SCHEMA,
  })
  @ApiResponse({
    status: 404,
    description: 'Video not found',
    schema: ERROR_SCHEMA,
  })
  @ApiResponse({
    status: 409,
    description: 'Video is not ready yet',
    schema: ERROR_SCHEMA,
  })
  async stream(
    @Param() params: VideoSlugParamDto,
    @CurrentUser() user?: JwtPayload,
  ): Promise<RedirectResponse> {
    const url = await this.videosService.getStreamUrl(params.slug, user?.sub);
    return { url, statusCode: HttpStatus.FOUND };
  }

  @Public()
  @Get(':slug/download')
  @Redirect()
  @ApiOperation({
    summary: 'Download a video',
    description:
      'Redirects (302) to a short-lived presigned URL that serves the original file as an attachment with its original file name.',
  })
  @ApiResponse({
    status: 302,
    description: 'Redirect to the downloadable file',
    headers: LOCATION_HEADER,
  })
  @ApiResponse({
    status: 400,
    description: 'Malformed slug',
    schema: ERROR_SCHEMA,
  })
  @ApiResponse({
    status: 404,
    description: 'Video not found',
    schema: ERROR_SCHEMA,
  })
  @ApiResponse({
    status: 409,
    description: 'Video is not ready yet',
    schema: ERROR_SCHEMA,
  })
  async download(
    @Param() params: VideoSlugParamDto,
    @CurrentUser() user?: JwtPayload,
  ): Promise<RedirectResponse> {
    const url = await this.videosService.getDownloadUrl(params.slug, user?.sub);
    return { url, statusCode: HttpStatus.FOUND };
  }

  @Public()
  @Get(':slug/thumbnail')
  @Redirect()
  @ApiOperation({
    summary: 'Get the video thumbnail',
    description:
      'Redirects (302) to a short-lived presigned URL of the JPEG thumbnail generated during processing.',
  })
  @ApiResponse({
    status: 302,
    description: 'Redirect to the thumbnail image',
    headers: LOCATION_HEADER,
  })
  @ApiResponse({
    status: 400,
    description: 'Malformed slug',
    schema: ERROR_SCHEMA,
  })
  @ApiResponse({
    status: 404,
    description: 'Video or thumbnail not found',
    schema: ERROR_SCHEMA,
  })
  async thumbnail(
    @Param() params: VideoSlugParamDto,
    @CurrentUser() user?: JwtPayload,
  ): Promise<RedirectResponse> {
    const url = await this.videosService.getThumbnailUrl(
      params.slug,
      user?.sub,
    );
    return { url, statusCode: HttpStatus.FOUND };
  }
}
