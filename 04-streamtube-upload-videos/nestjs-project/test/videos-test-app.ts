import { INestApplication, ValidationPipe } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Test } from '@nestjs/testing';
import { App } from 'supertest/types';
import { DataSource } from 'typeorm';
import { AppModule } from '../src/app.module';
import { DomainExceptionFilter } from '../src/common/filters/domain-exception.filter';
import { ValidationExceptionFilter } from '../src/common/filters/validation-exception.filter';
import { signPresignedUrlsWithInternalEndpoint } from '../src/test/storage';
import { createUserWithChannel } from '../src/test/video-factories';

/** Boots the full API with the same global pipes/filters as main.ts. */
export async function createVideosE2eApp(): Promise<INestApplication<App>> {
  // e2e runs inside the Compose network: sign client URLs with `minio:9000`.
  signPresignedUrlsWithInternalEndpoint();
  const moduleFixture = await Test.createTestingModule({
    imports: [AppModule],
  }).compile();

  const app = moduleFixture.createNestApplication<INestApplication<App>>();
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );
  app.useGlobalFilters(
    new DomainExceptionFilter(),
    new ValidationExceptionFilter(),
  );
  await app.init();
  return app;
}

/** Creates a confirmed user with a channel and returns a valid access token. */
export async function createAuthenticatedOwner(
  app: INestApplication<App>,
): Promise<{ userId: string; channelId: string; token: string }> {
  const { user, channel } = await createUserWithChannel(app.get(DataSource));
  const token = app.get(JwtService).sign({ sub: user.id, email: user.email });
  return { userId: user.id, channelId: channel.id, token };
}
