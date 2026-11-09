import { Test } from '@nestjs/testing';
import {
  InvalidVideoStatusException,
  VideoNotFoundException,
} from '../../common/exceptions/domain.exception';
import { StorageService } from '../../storage/storage.service';
import { VideoStatus } from '../videos.constants';
import { VideosService } from '../videos.service';
import { FfmpegService } from './ffmpeg.service';
import {
  thumbnailOffsetSeconds,
  VideoProcessingService,
} from './video-processing.service';

const METADATA = {
  format_name: 'mp4',
  bit_rate: 1000,
  width: 320,
  height: 240,
  video_codec: 'h264',
  audio_codec: 'aac',
  frame_rate: 25,
};

describe('thumbnailOffsetSeconds', () => {
  it.each([
    [120, 1],
    [1.5, 0.75],
    [null, 0],
    [0, 0],
  ])('duration %s → %s', (duration, expected) => {
    expect(thumbnailOffsetSeconds(duration)).toBe(expected);
  });
});

describe('VideoProcessingService', () => {
  let service: VideoProcessingService;
  let videos: {
    findById: jest.Mock;
    markReady: jest.Mock;
    markFailed: jest.Mock;
  };
  let storage: { presignInternalDownloadUrl: jest.Mock; putObject: jest.Mock };
  let ffmpeg: { probe: jest.Mock; extractFrame: jest.Mock };

  beforeEach(async () => {
    videos = {
      findById: jest.fn().mockResolvedValue({
        id: 'video-1',
        status: VideoStatus.PROCESSING,
        video_key: 'videos/video-1/source',
      }),
      markReady: jest.fn().mockResolvedValue(undefined),
      markFailed: jest.fn().mockResolvedValue(undefined),
    };
    storage = {
      presignInternalDownloadUrl: jest
        .fn()
        .mockResolvedValue('http://minio:9000/signed'),
      putObject: jest.fn().mockResolvedValue(undefined),
    };
    ffmpeg = {
      probe: jest
        .fn()
        .mockResolvedValue({ durationSeconds: 10, metadata: METADATA }),
      extractFrame: jest
        .fn()
        .mockResolvedValue(Buffer.from([0xff, 0xd8, 0xff])),
    };
    const moduleRef = await Test.createTestingModule({
      providers: [
        VideoProcessingService,
        { provide: VideosService, useValue: videos },
        { provide: StorageService, useValue: storage },
        { provide: FfmpegService, useValue: ffmpeg },
      ],
    }).compile();
    service = moduleRef.get(VideoProcessingService);
  });

  it('should probe the presigned source, store the thumbnail and mark the video ready', async () => {
    await service.process('video-1');

    expect(ffmpeg.probe).toHaveBeenCalledWith('http://minio:9000/signed');
    expect(ffmpeg.extractFrame).toHaveBeenCalledWith(
      'http://minio:9000/signed',
      1,
    );
    expect(storage.putObject).toHaveBeenCalledWith(
      'videos/video-1/thumbnail.jpg',
      expect.any(Buffer),
      'image/jpeg',
    );
    expect(videos.markReady).toHaveBeenCalledWith('video-1', {
      durationSeconds: 10,
      metadata: METADATA,
      thumbnailKey: 'videos/video-1/thumbnail.jpg',
    });
  });

  it('should be a no-op for videos that are already ready', async () => {
    videos.findById.mockResolvedValue({
      id: 'video-1',
      status: VideoStatus.READY,
    });

    await service.process('video-1');

    expect(ffmpeg.probe).not.toHaveBeenCalled();
    expect(videos.markReady).not.toHaveBeenCalled();
  });

  it('should throw VideoNotFoundException for deleted videos', async () => {
    videos.findById.mockResolvedValue(null);

    await expect(service.process('video-1')).rejects.toBeInstanceOf(
      VideoNotFoundException,
    );
  });

  it('should refuse videos that are not processing', async () => {
    videos.findById.mockResolvedValue({
      id: 'video-1',
      status: VideoStatus.DRAFT,
    });

    await expect(service.process('video-1')).rejects.toBeInstanceOf(
      InvalidVideoStatusException,
    );
  });

  it('should not mark ready when thumbnail generation fails', async () => {
    ffmpeg.extractFrame.mockRejectedValue(new Error('ffmpeg crashed'));

    await expect(service.process('video-1')).rejects.toThrow('ffmpeg crashed');
    expect(videos.markReady).not.toHaveBeenCalled();
  });
});
