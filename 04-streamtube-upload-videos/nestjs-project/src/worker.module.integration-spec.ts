import { getQueueToken } from '@nestjs/bullmq';
import { INestApplicationContext } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { Queue } from 'bullmq';
import { VideoProcessor } from './videos/processing/video.processor';
import { VIDEO_PROCESSING_QUEUE } from './videos/videos.constants';
import { WorkerModule } from './worker.module';

describe('WorkerModule (integration — Postgres + Redis)', () => {
  let app: INestApplicationContext;

  beforeAll(async () => {
    app = await NestFactory.createApplicationContext(WorkerModule, {
      logger: false,
    });
  });

  afterAll(async () => {
    await app.close();
  });

  it('should boot without an HTTP server and register the queue consumer', () => {
    expect(app.get(VideoProcessor)).toBeInstanceOf(VideoProcessor);
  });

  it('should connect the consumer to the video-processing queue', async () => {
    const processor = app.get(VideoProcessor);
    await processor.worker.waitUntilReady();

    expect(processor.worker.name).toBe(VIDEO_PROCESSING_QUEUE);
    expect(processor.worker.isRunning()).toBe(true);
    const queue = app.get<Queue>(getQueueToken(VIDEO_PROCESSING_QUEUE));
    expect(queue.name).toBe(VIDEO_PROCESSING_QUEUE);
  });
});
