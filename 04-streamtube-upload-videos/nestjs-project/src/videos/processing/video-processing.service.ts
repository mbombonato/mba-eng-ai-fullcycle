import { Injectable, Logger } from '@nestjs/common';
import {
  InvalidVideoStatusException,
  VideoNotFoundException,
} from '../../common/exceptions/domain.exception';
import { StorageService } from '../../storage/storage.service';
import {
  PROCESSING_SOURCE_URL_EXPIRATION_SECONDS,
  THUMBNAIL_CONTENT_TYPE,
  THUMBNAIL_MAX_OFFSET_SECONDS,
  VideoStatus,
  videoThumbnailKey,
} from '../videos.constants';
import { VideosService } from '../videos.service';
import { FfmpegService } from './ffmpeg.service';

/** Frame used as thumbnail: 1s in, or the middle of clips shorter than 2s. */
export function thumbnailOffsetSeconds(durationSeconds: number | null): number {
  if (!durationSeconds || durationSeconds <= 0) return 0;
  return Math.min(THUMBNAIL_MAX_OFFSET_SECONDS, durationSeconds / 2);
}

@Injectable()
export class VideoProcessingService {
  private readonly logger = new Logger(VideoProcessingService.name);

  constructor(
    private readonly videosService: VideosService,
    private readonly storageService: StorageService,
    private readonly ffmpegService: FfmpegService,
  ) {}

  /**
   * Extracts duration/metadata and generates the thumbnail, reading the
   * source through a presigned internal URL (FFmpeg uses range requests —
   * the 10 GB file is never copied). Idempotent for ready videos.
   */
  async process(videoId: string): Promise<void> {
    const video = await this.videosService.findById(videoId);
    if (!video) {
      throw new VideoNotFoundException();
    }
    if (video.status === VideoStatus.READY) {
      this.logger.log(`Video ${videoId} already ready — skipping`);
      return;
    }
    if (video.status !== VideoStatus.PROCESSING) {
      throw new InvalidVideoStatusException();
    }

    const sourceUrl = await this.storageService.presignInternalDownloadUrl(
      video.video_key,
      PROCESSING_SOURCE_URL_EXPIRATION_SECONDS,
    );
    const probe = await this.ffmpegService.probe(sourceUrl);
    const frame = await this.ffmpegService.extractFrame(
      sourceUrl,
      thumbnailOffsetSeconds(probe.durationSeconds),
    );

    const thumbnailKey = videoThumbnailKey(video.id);
    await this.storageService.putObject(
      thumbnailKey,
      frame,
      THUMBNAIL_CONTENT_TYPE,
    );
    await this.videosService.markReady(video.id, {
      durationSeconds: probe.durationSeconds,
      metadata: probe.metadata,
      thumbnailKey,
    });
    this.logger.log(`Video ${videoId} processed (${probe.durationSeconds}s)`);
  }

  async markFailed(videoId: string, reason: string): Promise<void> {
    await this.videosService.markFailed(videoId, reason);
  }
}
