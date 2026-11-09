import { TestingModule } from '@nestjs/testing';
import { readFileSync } from 'node:fs';
import { DataSource, Repository } from 'typeorm';
import { NotAVideoFileException } from '../../common/exceptions/domain.exception';
import { StorageModule } from '../../storage/storage.module';
import { StorageService } from '../../storage/storage.service';
import { cleanAllTables } from '../../test/create-test-data-source';
import {
  createMediaDir,
  generateTestVideo,
  JPEG_MAGIC,
  writeNotAVideo,
} from '../../test/media';
import { buildVideo, createUserWithChannel } from '../../test/video-factories';
import { createVideosTestingModule } from '../../test/videos-testing-module';
import { Video } from '../entities/video.entity';
import { VideoStatus, videoThumbnailKey } from '../videos.constants';
import { VideosModule } from '../videos.module';
import { FfmpegService } from './ffmpeg.service';
import { VideoProcessingService } from './video-processing.service';

describe('VideoProcessingService (integration — Postgres + MinIO + FFmpeg)', () => {
  let moduleRef: TestingModule;
  let service: VideoProcessingService;
  let storage: StorageService;
  let dataSource: DataSource;
  let videoRepository: Repository<Video>;
  const media = createMediaDir();
  let sampleVideo: Buffer;

  beforeAll(async () => {
    // The queue consumer (VideoProcessor) is deliberately not registered:
    // this suite drives the processing service directly.
    moduleRef = await createVideosTestingModule(
      [VideosModule, StorageModule],
      [VideoProcessingService, FfmpegService],
    );
    service = moduleRef.get(VideoProcessingService);
    storage = moduleRef.get(StorageService);
    dataSource = moduleRef.get(DataSource);
    videoRepository = dataSource.getRepository(Video);
    sampleVideo = readFileSync(generateTestVideo(media.dir, { seconds: 3 }));
  });

  afterAll(async () => {
    await moduleRef.close();
    media.cleanup();
  });

  beforeEach(async () => {
    await cleanAllTables(dataSource);
  });

  async function seedProcessingVideo(content: Buffer): Promise<Video> {
    const { channel } = await createUserWithChannel(dataSource);
    const video = await videoRepository.save(
      buildVideo(channel.id, {
        status: VideoStatus.PROCESSING,
        upload_id: null,
        file_size: content.length,
      }),
    );
    await storage.putObject(video.video_key, content, 'video/mp4');
    return video;
  }

  it('should extract duration and metadata, store the thumbnail and mark the video ready', async () => {
    const video = await seedProcessingVideo(sampleVideo);

    await service.process(video.id);

    const processed = await videoRepository.findOneByOrFail({ id: video.id });
    expect(processed.status).toBe(VideoStatus.READY);
    expect(processed.duration_seconds).toBeCloseTo(3, 0);
    expect(processed.metadata).toMatchObject({
      width: 320,
      height: 240,
      video_codec: 'h264',
      audio_codec: 'aac',
    });
    expect(processed.thumbnail_key).toBe(videoThumbnailKey(video.id));
    expect(processed.processed_at).toBeInstanceOf(Date);

    const thumbnailUrl = await storage.presignInternalDownloadUrl(
      processed.thumbnail_key!,
      60,
    );
    const thumbnail = Buffer.from(
      await (await fetch(thumbnailUrl)).arrayBuffer(),
    );
    expect(thumbnail.subarray(0, 3)).toEqual(JPEG_MAGIC);

    await storage.deleteObject(video.video_key);
    await storage.deleteObject(processed.thumbnail_key!);
  });

  it('should raise NotAVideoFileException for a non-video upload', async () => {
    const video = await seedProcessingVideo(
      readFileSync(writeNotAVideo(media.dir)),
    );

    await expect(service.process(video.id)).rejects.toBeInstanceOf(
      NotAVideoFileException,
    );
    const unchanged = await videoRepository.findOneByOrFail({ id: video.id });
    expect(unchanged.status).toBe(VideoStatus.PROCESSING);
    await storage.deleteObject(video.video_key);
  });

  it('should persist failures through markFailed', async () => {
    const video = await seedProcessingVideo(Buffer.from('x'));

    await service.markFailed(video.id, 'File is not a valid video');

    const failed = await videoRepository.findOneByOrFail({ id: video.id });
    expect(failed.status).toBe(VideoStatus.FAILED);
    expect(failed.failure_reason).toBe('File is not a valid video');
    await storage.deleteObject(video.video_key);
  });
});
