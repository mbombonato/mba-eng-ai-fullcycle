import { ApiProperty } from '@nestjs/swagger';
import { VideoResponseDto } from './video-response.dto';

export class UploadPartUrlDto {
  @ApiProperty({ example: 1 })
  part_number: number;

  @ApiProperty({
    description:
      'Presigned URL — PUT the part bytes here and keep the ETag response header',
  })
  url: string;
}

export class MultipartUploadDto {
  @ApiProperty()
  upload_id: string;

  @ApiProperty({
    example: 104857600,
    description: 'Bytes per part (last part may be smaller)',
  })
  part_size: number;

  @ApiProperty({ example: 103 })
  part_count: number;

  @ApiProperty({ type: String, format: 'date-time' })
  expires_at: string;

  @ApiProperty({ type: [UploadPartUrlDto] })
  parts: UploadPartUrlDto[];
}

export class CreateVideoResponseDto {
  @ApiProperty({ type: VideoResponseDto })
  video: VideoResponseDto;

  @ApiProperty({ type: MultipartUploadDto })
  upload: MultipartUploadDto;
}
