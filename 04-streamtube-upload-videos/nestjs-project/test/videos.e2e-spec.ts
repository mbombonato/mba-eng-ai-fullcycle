import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { App } from 'supertest/types';
import { DataSource } from 'typeorm';
import { cleanAllTables } from '../src/test/create-test-data-source';
import { putPart } from '../src/test/storage';
import { buildVideo } from '../src/test/video-factories';
import { Video } from '../src/videos/entities/video.entity';
import {
  VIDEO_MAX_FILE_SIZE_BYTES,
  VideoStatus,
} from '../src/videos/videos.constants';
import {
  createAuthenticatedOwner,
  createVideosE2eApp,
} from './videos-test-app';

const MIB = 1024 * 1024;

describe('Videos (e2e)', () => {
  let app: INestApplication<App>;
  let dataSource: DataSource;

  beforeAll(async () => {
    app = await createVideosE2eApp();
    dataSource = app.get(DataSource);
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(async () => {
    await cleanAllTables(dataSource);
  });

  const validBody = {
    title: '  Minha viagem  ',
    file_name: 'viagem.mp4',
    file_size: VIDEO_MAX_FILE_SIZE_BYTES,
    content_type: 'video/mp4',
  };

  describe('POST /videos', () => {
    it('should pre-register a draft and return presigned part URLs for a 10 GB upload', async () => {
      const { channelId, token } = await createAuthenticatedOwner(app);

      const res = await request(app.getHttpServer())
        .post('/videos')
        .set('Authorization', `Bearer ${token}`)
        .send(validBody)
        .expect(201);

      expect(res.body.video).toMatchObject({
        title: 'Minha viagem',
        status: 'draft',
        channel_id: channelId,
        file_size: VIDEO_MAX_FILE_SIZE_BYTES,
        mime_type: 'video/mp4',
      });
      expect(res.body.video.slug).toMatch(/^[A-Za-z0-9_-]{11}$/);
      expect(res.body.upload.part_size).toBe(100 * MIB);
      expect(res.body.upload.part_count).toBe(103);
      expect(res.body.upload.parts).toHaveLength(103);
      expect(res.body.upload.parts[0]).toMatchObject({ part_number: 1 });
      expect(res.body.upload.parts[0].url).toContain('X-Amz-Signature');

      const stored = await dataSource
        .getRepository(Video)
        .findOneByOrFail({ id: res.body.video.id });
      expect(stored.status).toBe(VideoStatus.DRAFT);
    });

    it('should reject files above 10 GB', async () => {
      const { token } = await createAuthenticatedOwner(app);

      const res = await request(app.getHttpServer())
        .post('/videos')
        .set('Authorization', `Bearer ${token}`)
        .send({ ...validBody, file_size: VIDEO_MAX_FILE_SIZE_BYTES + 1 })
        .expect(400);

      expect(res.body.error).toBe('VALIDATION_ERROR');
    });

    it('should reject non-video content types and missing titles', async () => {
      const { token } = await createAuthenticatedOwner(app);

      const res = await request(app.getHttpServer())
        .post('/videos')
        .set('Authorization', `Bearer ${token}`)
        .send({ ...validBody, title: '   ', content_type: 'application/pdf' })
        .expect(400);

      expect(res.body.message).toEqual(
        expect.arrayContaining([
          'content_type must be a video MIME type',
          'title should not be empty',
        ]),
      );
    });

    it('should require authentication', async () => {
      await request(app.getHttpServer())
        .post('/videos')
        .send(validBody)
        .expect(401);
    });
  });

  describe('POST /videos/:slug/upload/complete', () => {
    async function startSmallUpload(token: string, content: Buffer) {
      const res = await request(app.getHttpServer())
        .post('/videos')
        .set('Authorization', `Bearer ${token}`)
        .send({ ...validBody, file_size: content.length })
        .expect(201);
      return res.body as {
        video: { slug: string; id: string };
        upload: { parts: { part_number: number; url: string }[] };
      };
    }

    it('should complete the upload and move the video to processing', async () => {
      const { token } = await createAuthenticatedOwner(app);
      const content = Buffer.from('not-really-a-video');
      const { video, upload } = await startSmallUpload(token, content);
      const etag = await putPart(upload.parts[0].url, content);

      const res = await request(app.getHttpServer())
        .post(`/videos/${video.slug}/upload/complete`)
        .set('Authorization', `Bearer ${token}`)
        .send({ parts: [{ part_number: 1, etag }] })
        .expect(200);

      expect(res.body.status).toBe('processing');
      expect(res.body.file_size).toBe(content.length);
    });

    it('should return 400 INVALID_UPLOAD_PARTS for unknown ETags', async () => {
      const { token } = await createAuthenticatedOwner(app);
      const content = Buffer.from('abc');
      const { video, upload } = await startSmallUpload(token, content);
      await putPart(upload.parts[0].url, content);

      const res = await request(app.getHttpServer())
        .post(`/videos/${video.slug}/upload/complete`)
        .set('Authorization', `Bearer ${token}`)
        .send({ parts: [{ part_number: 1, etag: '"deadbeef"' }] })
        .expect(400);

      expect(res.body.error).toBe('INVALID_UPLOAD_PARTS');
    });

    it('should return 404 to users who do not own the video', async () => {
      const owner = await createAuthenticatedOwner(app);
      const intruder = await createAuthenticatedOwner(app);
      const { video } = await startSmallUpload(owner.token, Buffer.from('abc'));

      const res = await request(app.getHttpServer())
        .post(`/videos/${video.slug}/upload/complete`)
        .set('Authorization', `Bearer ${intruder.token}`)
        .send({ parts: [{ part_number: 1, etag: '"x"' }] })
        .expect(404);

      expect(res.body.error).toBe('VIDEO_NOT_FOUND');
    });

    it('should return 409 when the video is not a draft', async () => {
      const { channelId, token } = await createAuthenticatedOwner(app);
      const video = await dataSource
        .getRepository(Video)
        .save(
          buildVideo(channelId, { status: VideoStatus.READY, upload_id: null }),
        );

      const res = await request(app.getHttpServer())
        .post(`/videos/${video.slug}/upload/complete`)
        .set('Authorization', `Bearer ${token}`)
        .send({ parts: [{ part_number: 1, etag: '"x"' }] })
        .expect(409);

      expect(res.body.error).toBe('INVALID_VIDEO_STATUS');
    });

    it('should validate the part list and the slug format', async () => {
      const { token } = await createAuthenticatedOwner(app);

      await request(app.getHttpServer())
        .post('/videos/AbCdEfGhIjK/upload/complete')
        .set('Authorization', `Bearer ${token}`)
        .send({ parts: [] })
        .expect(400);
      await request(app.getHttpServer())
        .post('/videos/not-a-slug/upload/complete')
        .set('Authorization', `Bearer ${token}`)
        .send({ parts: [{ part_number: 1, etag: '"x"' }] })
        .expect(400);
    });
  });

  describe('GET /videos/:slug and media redirects', () => {
    it('should hide drafts from anonymous users and show them to the owner', async () => {
      const { channelId, token } = await createAuthenticatedOwner(app);
      const video = await dataSource
        .getRepository(Video)
        .save(buildVideo(channelId));

      await request(app.getHttpServer())
        .get(`/videos/${video.slug}`)
        .expect(404);
      const res = await request(app.getHttpServer())
        .get(`/videos/${video.slug}`)
        .set('Authorization', `Bearer ${token}`)
        .expect(200);

      expect(res.body).toMatchObject({ slug: video.slug, status: 'draft' });
    });

    it('should treat an invalid token on a public route as anonymous', async () => {
      const { channelId } = await createAuthenticatedOwner(app);
      const video = await dataSource
        .getRepository(Video)
        .save(
          buildVideo(channelId, { status: VideoStatus.READY, upload_id: null }),
        );

      await request(app.getHttpServer())
        .get(`/videos/${video.slug}`)
        .set('Authorization', 'Bearer garbage')
        .expect(200);
    });

    it('should return 409 VIDEO_NOT_READY when the owner streams a processing video', async () => {
      const { channelId, token } = await createAuthenticatedOwner(app);
      const video = await dataSource
        .getRepository(Video)
        .save(buildVideo(channelId, { status: VideoStatus.PROCESSING }));

      const res = await request(app.getHttpServer())
        .get(`/videos/${video.slug}/stream`)
        .set('Authorization', `Bearer ${token}`)
        .expect(409);

      expect(res.body.error).toBe('VIDEO_NOT_READY');
    });

    it('should return 404 THUMBNAIL_NOT_AVAILABLE before processing', async () => {
      const { channelId, token } = await createAuthenticatedOwner(app);
      const video = await dataSource
        .getRepository(Video)
        .save(buildVideo(channelId));

      const res = await request(app.getHttpServer())
        .get(`/videos/${video.slug}/thumbnail`)
        .set('Authorization', `Bearer ${token}`)
        .expect(404);

      expect(res.body.error).toBe('THUMBNAIL_NOT_AVAILABLE');
    });

    it('should redirect stream and download of a ready video to presigned storage URLs', async () => {
      const { channelId } = await createAuthenticatedOwner(app);
      const video = await dataSource
        .getRepository(Video)
        .save(
          buildVideo(channelId, { status: VideoStatus.READY, upload_id: null }),
        );

      const stream = await request(app.getHttpServer())
        .get(`/videos/${video.slug}/stream`)
        .expect(302);
      const download = await request(app.getHttpServer())
        .get(`/videos/${video.slug}/download`)
        .expect(302);

      expect(stream.headers.location).toContain(video.video_key);
      expect(stream.headers.location).toContain('X-Amz-Signature');
      expect(download.headers.location).toContain(
        'response-content-disposition=attachment',
      );
    });

    it('should return 404 for unknown slugs', async () => {
      const res = await request(app.getHttpServer())
        .get('/videos/AAAAAAAAAAA')
        .expect(404);

      expect(res.body.error).toBe('VIDEO_NOT_FOUND');
    });
  });
});
