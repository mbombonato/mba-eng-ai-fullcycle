import { getQueueToken } from '@nestjs/bullmq';
import { TestingModule } from '@nestjs/testing';
import { Queue } from 'bullmq';
import { DataSource } from 'typeorm';
import { InvalidVideoStatusException } from '../common/exceptions/domain.exception';
import { StorageService } from '../storage/storage.service';
import { cleanAllTables } from '../test/create-test-data-source';
import { putPart } from '../test/storage';
import { createUserWithChannel } from '../test/video-factories';
import { createVideosTestingModule } from '../test/videos-testing-module';
import { Video } from './entities/video.entity';
import {
  PROCESS_VIDEO_JOB,
  VIDEO_PROCESSING_QUEUE,
  VideoStatus,
} from './videos.constants';
import { VideosModule } from './videos.module';
import { VideosService } from './videos.service';

describe('VideosService (integration — Postgres + MinIO + Redis)', () => {
  let moduleRef: TestingModule;
  let service: VideosService;
  let storage: StorageService;
  let dataSource: DataSource;
  let queue: Queue;

  beforeAll(async () => {
    moduleRef = await createVideosTestingModule([VideosModule]);
    service = moduleRef.get(VideosService);
    storage = moduleRef.get(StorageService);
    dataSource = moduleRef.get(DataSource);
    queue = moduleRef.get<Queue>(getQueueToken(VIDEO_PROCESSING_QUEUE));
  });

  afterAll(async () => {
    await moduleRef.close();
  });

  beforeEach(async () => {
    await cleanAllTables(dataSource);
  });

  async function startUpload(userId: string, content: Buffer) {
    return service.createUpload(userId, {
      title: 'Integration video',
      file_name: 'integration.mp4',
      file_size: content.length,
      content_type: 'video/mp4',
    });
  }

  it('should persist a draft in the user channel and open the multipart upload', async () => {
    const { user, channel } = await createUserWithChannel(dataSource);

    const session = await startUpload(user.id, Buffer.from('bytes'));

    const stored = await dataSource
      .getRepository(Video)
      .findOneByOrFail({ id: session.video.id });
    expect(stored.status).toBe(VideoStatus.DRAFT);
    expect(stored.channel_id).toBe(channel.id);
    expect(stored.upload_id).toBe(session.uploadId);
    expect(session.parts).toHaveLength(1);
    await storage.abortMultipartUpload(stored.video_key, session.uploadId);
  });

  it('should generate distinct slugs for every video', async () => {
    const { user } = await createUserWithChannel(dataSource);

    const sessions = await Promise.all(
      Array.from({ length: 5 }, () => startUpload(user.id, Buffer.from('x'))),
    );

    const slugs = new Set(sessions.map((s) => s.video.slug));
    expect(slugs.size).toBe(5);
    await Promise.all(
      sessions.map((s) =>
        storage.abortMultipartUpload(s.video.video_key, s.uploadId),
      ),
    );
  });

  it('should complete the upload, store the real size and enqueue the processing job', async () => {
    const { user } = await createUserWithChannel(dataSource);
    const content = Buffer.from('fake-video-content');
    const session = await startUpload(user.id, content);
    const etag = await putPart(session.parts[0].url, content);

    const video = await service.completeUpload(user.id, session.video.slug, {
      parts: [{ part_number: 1, etag }],
    });

    expect(video.status).toBe(VideoStatus.PROCESSING);
    const stored = await dataSource
      .getRepository(Video)
      .findOneByOrFail({ id: video.id });
    expect(stored.file_size).toBe(content.length);
    expect(stored.upload_id).toBeNull();
    expect((await storage.headObject(stored.video_key)).size).toBe(
      content.length,
    );

    const job = await queue.getJob(video.id);
    expect(job?.name).toBe(PROCESS_VIDEO_JOB);
    expect(job?.data).toEqual({ videoId: video.id });
    expect(job?.opts.attempts).toBe(3);
    await storage.deleteObject(stored.video_key);
  });

  it('should refuse to complete the same upload twice', async () => {
    const { user } = await createUserWithChannel(dataSource);
    const content = Buffer.from('fake');
    const session = await startUpload(user.id, content);
    const etag = await putPart(session.parts[0].url, content);
    const dto = { parts: [{ part_number: 1, etag }] };
    await service.completeUpload(user.id, session.video.slug, dto);

    await expect(
      service.completeUpload(user.id, session.video.slug, dto),
    ).rejects.toBeInstanceOf(InvalidVideoStatusException);
    await storage.deleteObject(session.video.video_key);
  });
});
