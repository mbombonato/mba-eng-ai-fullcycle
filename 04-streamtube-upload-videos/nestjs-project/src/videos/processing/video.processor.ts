import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Logger } from '@nestjs/common';
import { Job, UnrecoverableError } from 'bullmq';
import {
  InvalidVideoStatusException,
  NotAVideoFileException,
  VideoNotFoundException,
} from '../../common/exceptions/domain.exception';
import { VIDEO_PROCESSING_QUEUE } from '../videos.constants';
import type { VideoProcessingJobData } from '../videos.types';
import { VideoProcessingService } from './video-processing.service';

/**
 * Queue consumer — registered only in the worker process (WorkerModule).
 * Background context: errors are logged and translated into BullMQ outcomes
 * (retry vs. terminal failure) instead of propagating to an HTTP caller.
 */
@Processor(VIDEO_PROCESSING_QUEUE)
export class VideoProcessor extends WorkerHost {
  private readonly logger = new Logger(VideoProcessor.name);

  constructor(private readonly processingService: VideoProcessingService) {
    super();
  }

  async process(job: Job<VideoProcessingJobData>): Promise<void> {
    const { videoId } = job.data;
    try {
      await this.processingService.process(videoId);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.logger.error(
        `Processing failed for video ${videoId} (attempt ${job.attemptsMade + 1}): ${message}`,
      );

      if (err instanceof NotAVideoFileException) {
        await this.processingService.markFailed(videoId, message);
        throw new UnrecoverableError(message);
      }
      if (
        err instanceof VideoNotFoundException ||
        err instanceof InvalidVideoStatusException
      ) {
        // Nothing to update — the job is stale. Do not retry.
        throw new UnrecoverableError(message);
      }
      if (this.isLastAttempt(job)) {
        await this.processingService.markFailed(videoId, message);
      }
      throw err;
    }
  }

  private isLastAttempt(job: Job): boolean {
    return job.attemptsMade + 1 >= (job.opts.attempts ?? 1);
  }
}
