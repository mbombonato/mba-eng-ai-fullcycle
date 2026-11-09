import { Test } from '@nestjs/testing';
import { Job, UnrecoverableError } from 'bullmq';
import {
  InvalidVideoStatusException,
  NotAVideoFileException,
  VideoNotFoundException,
} from '../../common/exceptions/domain.exception';
import type { VideoProcessingJobData } from '../videos.types';
import { VideoProcessingService } from './video-processing.service';
import { VideoProcessor } from './video.processor';

function makeJob(
  attemptsMade: number,
  attempts = 3,
): Job<VideoProcessingJobData> {
  return {
    data: { videoId: 'video-1' },
    attemptsMade,
    opts: { attempts },
  } as unknown as Job<VideoProcessingJobData>;
}

describe('VideoProcessor', () => {
  let processor: VideoProcessor;
  let processing: { process: jest.Mock; markFailed: jest.Mock };

  beforeEach(async () => {
    processing = {
      process: jest.fn().mockResolvedValue(undefined),
      markFailed: jest.fn().mockResolvedValue(undefined),
    };
    const moduleRef = await Test.createTestingModule({
      providers: [
        VideoProcessor,
        { provide: VideoProcessingService, useValue: processing },
      ],
    }).compile();
    processor = moduleRef.get(VideoProcessor);
    jest
      .spyOn(processor['logger'], 'error')
      .mockImplementation(() => undefined);
  });

  it('should process the video referenced by the job', async () => {
    await processor.process(makeJob(0));

    expect(processing.process).toHaveBeenCalledWith('video-1');
    expect(processing.markFailed).not.toHaveBeenCalled();
  });

  it('should rethrow transient errors without failing the video while attempts remain', async () => {
    processing.process.mockRejectedValue(new Error('storage timeout'));

    await expect(processor.process(makeJob(0))).rejects.toThrow(
      'storage timeout',
    );
    expect(processing.markFailed).not.toHaveBeenCalled();
  });

  it('should fail the video on the last attempt and rethrow', async () => {
    processing.process.mockRejectedValue(new Error('storage timeout'));

    await expect(processor.process(makeJob(2))).rejects.toThrow(
      'storage timeout',
    );
    expect(processing.markFailed).toHaveBeenCalledWith(
      'video-1',
      'storage timeout',
    );
  });

  it('should fail the video immediately and stop retries for non-video files', async () => {
    processing.process.mockRejectedValue(
      new NotAVideoFileException('no video stream found'),
    );

    await expect(processor.process(makeJob(0))).rejects.toBeInstanceOf(
      UnrecoverableError,
    );
    expect(processing.markFailed).toHaveBeenCalledWith(
      'video-1',
      'File is not a valid video: no video stream found',
    );
  });

  it.each([new VideoNotFoundException(), new InvalidVideoStatusException()])(
    'should stop retries without touching the DB for stale jobs (%s)',
    async (error) => {
      processing.process.mockRejectedValue(error);

      await expect(processor.process(makeJob(0))).rejects.toBeInstanceOf(
        UnrecoverableError,
      );
      expect(processing.markFailed).not.toHaveBeenCalled();
    },
  );
});
