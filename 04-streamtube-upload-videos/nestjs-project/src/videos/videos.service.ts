import { InjectQueue } from '@nestjs/bullmq';
import { Inject, Injectable, Logger } from '@nestjs/common';
import type { ConfigType } from '@nestjs/config';
import { InjectRepository } from '@nestjs/typeorm';
import { Queue } from 'bullmq';
import { randomUUID } from 'node:crypto';
import { QueryFailedError, Repository } from 'typeorm';
import { ChannelsService } from '../channels/channels.service';
import {
  ChannelNotFoundException,
  InvalidVideoStatusException,
  ThumbnailNotAvailableException,
  UploadSizeExceededException,
  VideoNotFoundException,
  VideoNotReadyException,
} from '../common/exceptions/domain.exception';
import videosConfig from '../config/videos.config';
import { StorageService } from '../storage/storage.service';
import { CompleteUploadDto } from './dto/complete-upload.dto';
import { CreateVideoDto } from './dto/create-video.dto';
import { Video } from './entities/video.entity';
import { generateVideoSlug } from './slug.util';
import {
  FAILURE_REASON_MAX_LENGTH,
  PROCESS_VIDEO_BACKOFF_MS,
  PROCESS_VIDEO_JOB,
  PROCESS_VIDEO_REMOVE_ON_COMPLETE,
  PROCESS_VIDEO_REMOVE_ON_FAIL,
  VIDEO_MAX_FILE_SIZE_BYTES,
  VIDEO_PROCESSING_QUEUE,
  VIDEO_SLUG_MAX_ATTEMPTS,
  VideoStatus,
  videoSourceKey,
} from './videos.constants';
import type {
  ProcessedVideoResult,
  VideoProcessingJobData,
} from './videos.types';

const PG_UNIQUE_VIOLATION = '23505';

export interface VideoUploadSession {
  video: Video;
  uploadId: string;
  partSize: number;
  partCount: number;
  expiresAt: Date;
  parts: { partNumber: number; url: string }[];
}

function isSlugUniqueViolation(err: unknown): boolean {
  if (!(err instanceof QueryFailedError)) return false;
  const driverError = err.driverError as { code?: string; detail?: string };
  return (
    driverError?.code === PG_UNIQUE_VIOLATION &&
    typeof driverError.detail === 'string' &&
    driverError.detail.includes('(slug)')
  );
}

@Injectable()
export class VideosService {
  private readonly logger = new Logger(VideosService.name);

  constructor(
    @InjectRepository(Video)
    private readonly videoRepository: Repository<Video>,
    private readonly channelsService: ChannelsService,
    private readonly storageService: StorageService,
    @InjectQueue(VIDEO_PROCESSING_QUEUE)
    private readonly processingQueue: Queue<VideoProcessingJobData>,
    @Inject(videosConfig.KEY)
    private readonly config: ConfigType<typeof videosConfig>,
  ) {}

  /**
   * Starts a direct-to-storage multipart upload and pre-registers the video
   * as a draft. No video byte passes through the API.
   */
  async createUpload(
    userId: string,
    dto: CreateVideoDto,
  ): Promise<VideoUploadSession> {
    const channel = await this.channelsService.findByUserId(userId);
    if (!channel) {
      throw new ChannelNotFoundException();
    }

    const videoId = randomUUID();
    const key = videoSourceKey(videoId);
    const partSize = this.config.uploadPartSizeBytes;
    const partCount = Math.ceil(dto.file_size / partSize);

    const uploadId = await this.storageService.createMultipartUpload(
      key,
      dto.content_type,
    );

    let video: Video;
    try {
      video = await this.insertDraftWithUniqueSlug({
        id: videoId,
        channel_id: channel.id,
        title: dto.title,
        status: VideoStatus.DRAFT,
        original_file_name: dto.file_name,
        mime_type: dto.content_type,
        file_size: dto.file_size,
        video_key: key,
        upload_id: uploadId,
      });
    } catch (err) {
      // Compensation: do not leave an orphan multipart upload behind.
      await this.storageService.abortMultipartUpload(key, uploadId);
      throw err;
    }

    const expiresIn = this.config.uploadUrlExpirationSeconds;
    const parts = await this.storageService.presignUploadParts(
      key,
      uploadId,
      partCount,
      expiresIn,
    );

    return {
      video,
      uploadId,
      partSize,
      partCount,
      expiresAt: new Date(Date.now() + expiresIn * 1000),
      parts,
    };
  }

  /**
   * Finishes the multipart upload, checks the real stored size and publishes
   * the processing job. Status: draft → processing.
   */
  async completeUpload(
    userId: string,
    slug: string,
    dto: CompleteUploadDto,
  ): Promise<Video> {
    const video = await this.findOwnedBySlug(slug, userId);
    if (video.status !== VideoStatus.DRAFT || !video.upload_id) {
      throw new InvalidVideoStatusException();
    }

    await this.storageService.completeMultipartUpload(
      video.video_key,
      video.upload_id,
      dto.parts.map((p) => ({ partNumber: p.part_number, etag: p.etag })),
    );

    const stored = await this.storageService.headObject(video.video_key);
    if (stored.size > VIDEO_MAX_FILE_SIZE_BYTES) {
      await this.storageService.deleteObject(video.video_key);
      await this.markFailed(
        video.id,
        `Uploaded file has ${stored.size} bytes, above the 10 GB limit`,
      );
      throw new UploadSizeExceededException();
    }

    video.status = VideoStatus.PROCESSING;
    video.file_size = stored.size;
    video.upload_id = null;
    const saved = await this.videoRepository.save(video);

    try {
      await this.processingQueue.add(
        PROCESS_VIDEO_JOB,
        { videoId: video.id },
        {
          jobId: video.id,
          attempts: this.config.processingAttempts,
          backoff: { type: 'exponential', delay: PROCESS_VIDEO_BACKOFF_MS },
          removeOnComplete: PROCESS_VIDEO_REMOVE_ON_COMPLETE,
          removeOnFail: PROCESS_VIDEO_REMOVE_ON_FAIL,
        },
      );
    } catch (err) {
      this.logger.error(`Failed to enqueue processing for video ${video.id}`);
      await this.markFailed(video.id, 'Failed to enqueue video processing');
      throw err;
    }

    return saved;
  }

  /** Ready videos are public; other statuses are visible only to the owner. */
  async findVisibleBySlug(slug: string, viewerUserId?: string): Promise<Video> {
    const video = await this.videoRepository.findOne({
      where: { slug },
      relations: { channel: true },
    });
    if (!video) {
      throw new VideoNotFoundException();
    }
    const isOwner =
      viewerUserId !== undefined && video.channel.user_id === viewerUserId;
    if (video.status !== VideoStatus.READY && !isOwner) {
      throw new VideoNotFoundException();
    }
    return video;
  }

  async getStreamUrl(slug: string, viewerUserId?: string): Promise<string> {
    const video = await this.findReadyVisibleBySlug(slug, viewerUserId);
    return this.storageService.presignDownloadUrl(video.video_key, {
      expiresIn: this.config.streamUrlExpirationSeconds,
      contentType: video.mime_type,
    });
  }

  async getDownloadUrl(slug: string, viewerUserId?: string): Promise<string> {
    const video = await this.findReadyVisibleBySlug(slug, viewerUserId);
    return this.storageService.presignDownloadUrl(video.video_key, {
      expiresIn: this.config.streamUrlExpirationSeconds,
      contentType: video.mime_type,
      downloadFileName: video.original_file_name,
    });
  }

  async getThumbnailUrl(slug: string, viewerUserId?: string): Promise<string> {
    const video = await this.findVisibleBySlug(slug, viewerUserId);
    if (!video.thumbnail_key) {
      throw new ThumbnailNotAvailableException();
    }
    return this.storageService.presignDownloadUrl(video.thumbnail_key, {
      expiresIn: this.config.streamUrlExpirationSeconds,
    });
  }

  async findById(id: string): Promise<Video | null> {
    return this.videoRepository.findOne({ where: { id } });
  }

  /** Status: processing → ready, persisting what the worker extracted. */
  async markReady(id: string, result: ProcessedVideoResult): Promise<void> {
    await this.videoRepository.update(
      { id },
      {
        status: VideoStatus.READY,
        duration_seconds: result.durationSeconds,
        metadata: result.metadata,
        thumbnail_key: result.thumbnailKey,
        failure_reason: null,
        processed_at: new Date(),
      },
    );
  }

  /** Terminal failure with a diagnosable reason. */
  async markFailed(id: string, reason: string): Promise<void> {
    await this.videoRepository.update(
      { id },
      {
        status: VideoStatus.FAILED,
        failure_reason: reason.slice(0, FAILURE_REASON_MAX_LENGTH),
      },
    );
  }

  private async findOwnedBySlug(slug: string, userId: string): Promise<Video> {
    const video = await this.videoRepository.findOne({
      where: { slug },
      relations: { channel: true },
    });
    // Non-owners get the same 404 as unknown slugs: drafts are not disclosed.
    if (!video || video.channel.user_id !== userId) {
      throw new VideoNotFoundException();
    }
    return video;
  }

  private async findReadyVisibleBySlug(
    slug: string,
    viewerUserId?: string,
  ): Promise<Video> {
    const video = await this.findVisibleBySlug(slug, viewerUserId);
    if (video.status !== VideoStatus.READY) {
      throw new VideoNotReadyException();
    }
    return video;
  }

  private async insertDraftWithUniqueSlug(
    data: Omit<Partial<Video>, 'slug'>,
  ): Promise<Video> {
    for (let attempt = 1; ; attempt++) {
      try {
        return await this.videoRepository.save(
          this.videoRepository.create({ ...data, slug: generateVideoSlug() }),
        );
      } catch (err) {
        if (!isSlugUniqueViolation(err) || attempt >= VIDEO_SLUG_MAX_ATTEMPTS) {
          throw err;
        }
        this.logger.warn(`Slug collision on attempt ${attempt}, retrying`);
      }
    }
  }
}
