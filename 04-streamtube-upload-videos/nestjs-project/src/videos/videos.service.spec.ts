import { getQueueToken } from '@nestjs/bullmq';
import { Test } from '@nestjs/testing';
import { getRepositoryToken } from '@nestjs/typeorm';
import { QueryFailedError } from 'typeorm';
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
import { Video } from './entities/video.entity';
import {
  PROCESS_VIDEO_JOB,
  VIDEO_MAX_FILE_SIZE_BYTES,
  VIDEO_PROCESSING_QUEUE,
  VIDEO_SLUG_PATTERN,
  VideoStatus,
} from './videos.constants';
import { VideosService } from './videos.service';

const MIB = 1024 * 1024;
const OWNER_ID = 'user-1';
const CHANNEL = { id: 'channel-1', user_id: OWNER_ID };

const mockConfig = {
  uploadPartSizeBytes: 100 * MIB,
  uploadUrlExpirationSeconds: 86400,
  streamUrlExpirationSeconds: 3600,
  processingAttempts: 3,
};

function slugViolation(): QueryFailedError {
  return new QueryFailedError('INSERT', [], {
    code: '23505',
    detail: 'Key (slug)=(abc) already exists.',
  } as unknown as Error);
}

function makeVideo(overrides: Partial<Video> = {}): Video {
  return {
    id: 'video-1',
    channel_id: CHANNEL.id,
    channel: CHANNEL,
    title: 'Trip',
    slug: 'AbCdEfGhIjK',
    status: VideoStatus.DRAFT,
    original_file_name: 'trip.mp4',
    mime_type: 'video/mp4',
    file_size: 10 * MIB,
    video_key: 'videos/video-1/source',
    upload_id: 'upload-1',
    thumbnail_key: null,
    duration_seconds: null,
    metadata: null,
    failure_reason: null,
    processed_at: null,
    ...overrides,
  } as Video;
}

describe('VideosService', () => {
  let service: VideosService;
  let repository: {
    save: jest.Mock;
    create: jest.Mock;
    findOne: jest.Mock;
    update: jest.Mock;
  };
  let storage: Record<
    keyof Pick<
      StorageService,
      | 'createMultipartUpload'
      | 'presignUploadParts'
      | 'abortMultipartUpload'
      | 'completeMultipartUpload'
      | 'headObject'
      | 'deleteObject'
      | 'presignDownloadUrl'
    >,
    jest.Mock
  >;
  let channels: { findByUserId: jest.Mock };
  let queue: { add: jest.Mock };

  beforeEach(async () => {
    repository = {
      save: jest.fn(async (v: Partial<Video>) => ({ ...v }) as Video),
      create: jest.fn((v: Partial<Video>) => v),
      findOne: jest.fn(),
      update: jest.fn().mockResolvedValue(undefined),
    };
    storage = {
      createMultipartUpload: jest.fn().mockResolvedValue('upload-1'),
      presignUploadParts: jest.fn(
        async (_key: string, _uploadId: string, count: number) =>
          Array.from({ length: count }, (_, i) => ({
            partNumber: i + 1,
            url: `http://storage/part-${i + 1}`,
          })),
      ),
      abortMultipartUpload: jest.fn().mockResolvedValue(undefined),
      completeMultipartUpload: jest.fn().mockResolvedValue(undefined),
      headObject: jest
        .fn()
        .mockResolvedValue({ size: 10 * MIB, contentType: 'video/mp4' }),
      deleteObject: jest.fn().mockResolvedValue(undefined),
      presignDownloadUrl: jest.fn().mockResolvedValue('http://storage/signed'),
    };
    channels = { findByUserId: jest.fn().mockResolvedValue(CHANNEL) };
    queue = { add: jest.fn().mockResolvedValue({ id: 'video-1' }) };

    const moduleRef = await Test.createTestingModule({
      providers: [
        VideosService,
        { provide: getRepositoryToken(Video), useValue: repository },
        { provide: ChannelsService, useValue: channels },
        { provide: StorageService, useValue: storage },
        { provide: getQueueToken(VIDEO_PROCESSING_QUEUE), useValue: queue },
        { provide: videosConfig.KEY, useValue: mockConfig },
      ],
    }).compile();
    service = moduleRef.get(VideosService);
  });

  describe('createUpload', () => {
    const dto = {
      title: 'Trip',
      file_name: 'trip.mp4',
      file_size: VIDEO_MAX_FILE_SIZE_BYTES,
      content_type: 'video/mp4',
    };

    it('should pre-register a draft and plan 103 parts of 100 MiB for 10 GiB', async () => {
      const session = await service.createUpload(OWNER_ID, dto);

      expect(session.partSize).toBe(100 * MIB);
      expect(session.partCount).toBe(103);
      expect(session.parts).toHaveLength(103);
      expect(session.video.status).toBe(VideoStatus.DRAFT);
      expect(session.video.channel_id).toBe(CHANNEL.id);
      expect(session.video.upload_id).toBe('upload-1');
      expect(session.video.slug).toMatch(VIDEO_SLUG_PATTERN);
      expect(session.video.video_key).toBe(`videos/${session.video.id}/source`);
      expect(storage.createMultipartUpload).toHaveBeenCalledWith(
        session.video.video_key,
        'video/mp4',
      );
    });

    it('should use a single part for files smaller than the part size', async () => {
      const session = await service.createUpload(OWNER_ID, {
        ...dto,
        file_size: 1024,
      });

      expect(session.partCount).toBe(1);
    });

    it('should throw ChannelNotFoundException when the user has no channel', async () => {
      channels.findByUserId.mockResolvedValue(null);

      await expect(service.createUpload(OWNER_ID, dto)).rejects.toBeInstanceOf(
        ChannelNotFoundException,
      );
      expect(storage.createMultipartUpload).not.toHaveBeenCalled();
    });

    it('should retry with a new slug on a unique slug violation', async () => {
      repository.save
        .mockRejectedValueOnce(slugViolation())
        .mockImplementationOnce(async (v: Partial<Video>) => v);

      const session = await service.createUpload(OWNER_ID, dto);

      expect(repository.save).toHaveBeenCalledTimes(2);
      const [first] = repository.save.mock.calls[0] as [Video];
      const [second] = repository.save.mock.calls[1] as [Video];
      expect(first.slug).not.toBe(second.slug);
      expect(session.video.slug).toBe(second.slug);
    });

    it('should abort the multipart upload when the draft cannot be persisted', async () => {
      repository.save.mockRejectedValue(slugViolation());

      await expect(service.createUpload(OWNER_ID, dto)).rejects.toBeInstanceOf(
        QueryFailedError,
      );
      expect(repository.save).toHaveBeenCalledTimes(5);
      expect(storage.abortMultipartUpload).toHaveBeenCalledWith(
        expect.stringMatching(/^videos\/.+\/source$/),
        'upload-1',
      );
    });
  });

  describe('completeUpload', () => {
    const dto = { parts: [{ part_number: 1, etag: '"etag-1"' }] };

    it('should complete, move to processing and enqueue the job with the video id', async () => {
      repository.findOne.mockResolvedValue(makeVideo());

      const video = await service.completeUpload(OWNER_ID, 'AbCdEfGhIjK', dto);

      expect(storage.completeMultipartUpload).toHaveBeenCalledWith(
        'videos/video-1/source',
        'upload-1',
        [{ partNumber: 1, etag: '"etag-1"' }],
      );
      expect(video.status).toBe(VideoStatus.PROCESSING);
      expect(video.upload_id).toBeNull();
      expect(queue.add).toHaveBeenCalledWith(
        PROCESS_VIDEO_JOB,
        { videoId: 'video-1' },
        expect.objectContaining({
          jobId: 'video-1',
          attempts: 3,
          backoff: { type: 'exponential', delay: 5000 },
        }),
      );
    });

    it('should store the real object size reported by the storage', async () => {
      repository.findOne.mockResolvedValue(makeVideo({ file_size: 1 }));
      storage.headObject.mockResolvedValue({
        size: 4242,
        contentType: 'video/mp4',
      });

      const video = await service.completeUpload(OWNER_ID, 'AbCdEfGhIjK', dto);

      expect(video.file_size).toBe(4242);
    });

    it('should hide videos of other users behind VideoNotFoundException', async () => {
      repository.findOne.mockResolvedValue(makeVideo());

      await expect(
        service.completeUpload('intruder', 'AbCdEfGhIjK', dto),
      ).rejects.toBeInstanceOf(VideoNotFoundException);
      expect(storage.completeMultipartUpload).not.toHaveBeenCalled();
    });

    it('should reject completion when the video is no longer a draft', async () => {
      repository.findOne.mockResolvedValue(
        makeVideo({ status: VideoStatus.PROCESSING, upload_id: null }),
      );

      await expect(
        service.completeUpload(OWNER_ID, 'AbCdEfGhIjK', dto),
      ).rejects.toBeInstanceOf(InvalidVideoStatusException);
    });

    it('should delete the object and fail the video when it exceeds 10 GiB', async () => {
      repository.findOne.mockResolvedValue(makeVideo());
      storage.headObject.mockResolvedValue({
        size: VIDEO_MAX_FILE_SIZE_BYTES + 1,
        contentType: 'video/mp4',
      });

      await expect(
        service.completeUpload(OWNER_ID, 'AbCdEfGhIjK', dto),
      ).rejects.toBeInstanceOf(UploadSizeExceededException);
      expect(storage.deleteObject).toHaveBeenCalledWith(
        'videos/video-1/source',
      );
      expect(repository.update).toHaveBeenCalledWith(
        { id: 'video-1' },
        expect.objectContaining({ status: VideoStatus.FAILED }),
      );
      expect(queue.add).not.toHaveBeenCalled();
    });

    it('should mark the video failed and rethrow when enqueueing fails', async () => {
      repository.findOne.mockResolvedValue(makeVideo());
      queue.add.mockRejectedValue(new Error('redis down'));

      await expect(
        service.completeUpload(OWNER_ID, 'AbCdEfGhIjK', dto),
      ).rejects.toThrow('redis down');
      expect(repository.update).toHaveBeenCalledWith(
        { id: 'video-1' },
        expect.objectContaining({
          status: VideoStatus.FAILED,
          failure_reason: 'Failed to enqueue video processing',
        }),
      );
    });
  });

  describe('visibility and delivery', () => {
    it('should expose ready videos to anonymous viewers', async () => {
      repository.findOne.mockResolvedValue(
        makeVideo({ status: VideoStatus.READY }),
      );

      const video = await service.findVisibleBySlug('AbCdEfGhIjK');

      expect(video.status).toBe(VideoStatus.READY);
    });

    it.each([VideoStatus.DRAFT, VideoStatus.PROCESSING, VideoStatus.FAILED])(
      'should hide %s videos from non-owners',
      async (status) => {
        repository.findOne.mockResolvedValue(makeVideo({ status }));

        await expect(
          service.findVisibleBySlug('AbCdEfGhIjK', 'someone-else'),
        ).rejects.toBeInstanceOf(VideoNotFoundException);
        await expect(
          service.findVisibleBySlug('AbCdEfGhIjK'),
        ).rejects.toBeInstanceOf(VideoNotFoundException);
      },
    );

    it('should show non-ready videos to their owner', async () => {
      repository.findOne.mockResolvedValue(
        makeVideo({ status: VideoStatus.PROCESSING }),
      );

      const video = await service.findVisibleBySlug('AbCdEfGhIjK', OWNER_ID);

      expect(video.status).toBe(VideoStatus.PROCESSING);
    });

    it('should throw VideoNotFoundException for unknown slugs', async () => {
      repository.findOne.mockResolvedValue(null);

      await expect(
        service.findVisibleBySlug('AbCdEfGhIjK'),
      ).rejects.toBeInstanceOf(VideoNotFoundException);
    });

    it('should sign an inline stream URL with the video content type', async () => {
      repository.findOne.mockResolvedValue(
        makeVideo({ status: VideoStatus.READY }),
      );

      const url = await service.getStreamUrl('AbCdEfGhIjK');

      expect(url).toBe('http://storage/signed');
      expect(storage.presignDownloadUrl).toHaveBeenCalledWith(
        'videos/video-1/source',
        { expiresIn: 3600, contentType: 'video/mp4' },
      );
    });

    it('should sign a download URL as attachment with the original file name', async () => {
      repository.findOne.mockResolvedValue(
        makeVideo({ status: VideoStatus.READY }),
      );

      await service.getDownloadUrl('AbCdEfGhIjK');

      expect(storage.presignDownloadUrl).toHaveBeenCalledWith(
        'videos/video-1/source',
        expect.objectContaining({ downloadFileName: 'trip.mp4' }),
      );
    });

    it('should refuse to stream a non-ready video to its owner', async () => {
      repository.findOne.mockResolvedValue(
        makeVideo({ status: VideoStatus.PROCESSING }),
      );

      await expect(
        service.getStreamUrl('AbCdEfGhIjK', OWNER_ID),
      ).rejects.toBeInstanceOf(VideoNotReadyException);
    });

    it('should report a missing thumbnail', async () => {
      repository.findOne.mockResolvedValue(
        makeVideo({ status: VideoStatus.PROCESSING }),
      );

      await expect(
        service.getThumbnailUrl('AbCdEfGhIjK', OWNER_ID),
      ).rejects.toBeInstanceOf(ThumbnailNotAvailableException);
    });
  });

  describe('status transitions used by the worker', () => {
    it('should mark a video ready with the extracted data', async () => {
      const metadata = {
        format_name: 'mp4',
        bit_rate: 1,
        width: 320,
        height: 240,
        video_codec: 'h264',
        audio_codec: null,
        frame_rate: 25,
      };

      await service.markReady('video-1', {
        durationSeconds: 2,
        metadata,
        thumbnailKey: 'videos/video-1/thumbnail.jpg',
      });

      expect(repository.update).toHaveBeenCalledWith(
        { id: 'video-1' },
        expect.objectContaining({
          status: VideoStatus.READY,
          duration_seconds: 2,
          metadata,
          thumbnail_key: 'videos/video-1/thumbnail.jpg',
          processed_at: expect.any(Date),
        }),
      );
    });

    it('should truncate very long failure reasons', async () => {
      await service.markFailed('video-1', 'x'.repeat(5000));

      const [, changes] = repository.update.mock.calls[0] as [
        unknown,
        { failure_reason: string },
      ];
      expect(changes.failure_reason).toHaveLength(1000);
    });
  });
});
