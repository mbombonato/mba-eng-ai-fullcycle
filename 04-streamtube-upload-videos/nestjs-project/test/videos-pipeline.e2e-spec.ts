import { INestApplication, INestApplicationContext } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { readFileSync } from 'node:fs';
import request from 'supertest';
import { App } from 'supertest/types';
import { DataSource } from 'typeorm';
import { StorageService } from '../src/storage/storage.service';
import { cleanAllTables } from '../src/test/create-test-data-source';
import {
  createMediaDir,
  generateTestVideo,
  JPEG_MAGIC,
  writeNotAVideo,
} from '../src/test/media';
import { putPart } from '../src/test/storage';
import { Video } from '../src/videos/entities/video.entity';
import { WorkerModule } from '../src/worker.module';
import {
  createAuthenticatedOwner,
  createVideosE2eApp,
} from './videos-test-app';

const PROCESSING_TIMEOUT_MS = 60_000;

/**
 * Full Phase 03 pipeline over real infrastructure: API → MinIO (direct
 * multipart upload) → BullMQ/Redis → worker (FFmpeg) → Postgres → streaming.
 */
describe('Video pipeline (e2e)', () => {
  let app: INestApplication<App>;
  let worker: INestApplicationContext;
  let dataSource: DataSource;
  const media = createMediaDir();

  beforeAll(async () => {
    app = await createVideosE2eApp();
    // In-process worker so the suite does not depend on the `worker`
    // container; if that container is up it may take the job instead —
    // both run the same code, so the outcome is identical.
    worker = await NestFactory.createApplicationContext(WorkerModule, {
      logger: false,
    });
    dataSource = app.get(DataSource);
  });

  afterAll(async () => {
    await worker.close();
    await app.close();
    media.cleanup();
  });

  beforeEach(async () => {
    await cleanAllTables(dataSource);
  });

  async function uploadThroughPresignedUrls(
    token: string,
    content: Buffer,
    fileName: string,
  ): Promise<string> {
    const created = await request(app.getHttpServer())
      .post('/videos')
      .set('Authorization', `Bearer ${token}`)
      .send({
        title: 'Pipeline video',
        file_name: fileName,
        file_size: content.length,
        content_type: 'video/mp4',
      })
      .expect(201);
    const { slug } = created.body.video as { slug: string };
    const { parts, part_size: partSize } = created.body.upload as {
      parts: { part_number: number; url: string }[];
      part_size: number;
    };

    const uploaded = await Promise.all(
      parts.map(async (part) => ({
        part_number: part.part_number,
        etag: await putPart(
          part.url,
          content.subarray(
            (part.part_number - 1) * partSize,
            part.part_number * partSize,
          ),
        ),
      })),
    );

    const completed = await request(app.getHttpServer())
      .post(`/videos/${slug}/upload/complete`)
      .set('Authorization', `Bearer ${token}`)
      .send({ parts: uploaded })
      .expect(200);
    expect(completed.body.status).toBe('processing');
    return slug;
  }

  async function waitForTerminalStatus(
    slug: string,
    token: string,
  ): Promise<Record<string, any>> {
    const deadline = Date.now() + PROCESSING_TIMEOUT_MS;
    while (Date.now() < deadline) {
      const res = await request(app.getHttpServer())
        .get(`/videos/${slug}`)
        .set('Authorization', `Bearer ${token}`)
        .expect(200);
      if (res.body.status === 'ready' || res.body.status === 'failed') {
        return res.body as Record<string, any>;
      }
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    throw new Error(`Video ${slug} was not processed in time`);
  }

  it(
    'should upload, process, stream with 206 and download a video',
    async () => {
      const { token } = await createAuthenticatedOwner(app);
      const content = readFileSync(
        generateTestVideo(media.dir, { seconds: 3 }),
      );

      const slug = await uploadThroughPresignedUrls(
        token,
        content,
        'férias.mp4',
      );
      const video = await waitForTerminalStatus(slug, token);

      expect(video.status).toBe('ready');
      expect(video.duration_seconds).toBeCloseTo(3, 0);
      expect(video.metadata).toMatchObject({
        width: 320,
        height: 240,
        video_codec: 'h264',
      });
      expect(video.processed_at).not.toBeNull();

      // Public (anonymous) access once ready
      await request(app.getHttpServer()).get(`/videos/${slug}`).expect(200);

      // Streaming: redirect → storage answers Range with 206 Partial Content
      const stream = await request(app.getHttpServer())
        .get(`/videos/${slug}/stream`)
        .expect(302);
      const partial = await fetch(stream.headers.location, {
        headers: { Range: 'bytes=0-1023' },
      });
      expect(partial.status).toBe(206);
      expect(partial.headers.get('content-range')).toBe(
        `bytes 0-1023/${content.length}`,
      );
      expect(partial.headers.get('content-type')).toBe('video/mp4');
      expect((await partial.arrayBuffer()).byteLength).toBe(1024);

      // Download: original bytes as attachment with the original name
      const download = await request(app.getHttpServer())
        .get(`/videos/${slug}/download`)
        .expect(302);
      const file = await fetch(download.headers.location);
      expect(file.headers.get('content-disposition')).toContain('attachment');
      expect(file.headers.get('content-disposition')).toContain(
        `filename*=UTF-8''f%C3%A9rias.mp4`,
      );
      expect(Buffer.from(await file.arrayBuffer()).equals(content)).toBe(true);

      // Thumbnail generated from a frame
      const thumbnail = await request(app.getHttpServer())
        .get(`/videos/${slug}/thumbnail`)
        .expect(302);
      const image = Buffer.from(
        await (await fetch(thumbnail.headers.location)).arrayBuffer(),
      );
      expect(image.subarray(0, 3)).toEqual(JPEG_MAGIC);

      const stored = await dataSource
        .getRepository(Video)
        .findOneByOrFail({ slug });
      const storage = app.get(StorageService);
      await storage.deleteObject(stored.video_key);
      await storage.deleteObject(stored.thumbnail_key!);
    },
    PROCESSING_TIMEOUT_MS + 10_000,
  );

  it(
    'should mark a non-video upload as failed with a reason and keep it hidden',
    async () => {
      const { token } = await createAuthenticatedOwner(app);
      const content = readFileSync(writeNotAVideo(media.dir));

      const slug = await uploadThroughPresignedUrls(token, content, 'fake.mp4');
      const video = await waitForTerminalStatus(slug, token);

      expect(video.status).toBe('failed');
      expect(video.failure_reason).toContain('File is not a valid video');
      await request(app.getHttpServer()).get(`/videos/${slug}`).expect(404);

      const stored = await dataSource
        .getRepository(Video)
        .findOneByOrFail({ slug });
      await app.get(StorageService).deleteObject(stored.video_key);
    },
    PROCESSING_TIMEOUT_MS + 10_000,
  );
});
