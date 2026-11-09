import { S3Client } from '@aws-sdk/client-s3';
import { ConfigModule } from '@nestjs/config';
import { Test } from '@nestjs/testing';
import storageConfig from '../config/storage.config';
import { S3_CLIENT, S3_PRESIGN_CLIENT } from './storage.constants';
import { StorageModule } from './storage.module';
import { StorageService } from './storage.service';

describe('StorageModule', () => {
  const originalEnv = { ...process.env };

  afterEach(() => {
    process.env = { ...originalEnv };
  });

  it('should build internal and presign clients with their own endpoints', async () => {
    process.env.S3_ENDPOINT = 'http://minio:9000';
    process.env.S3_PUBLIC_ENDPOINT = 'http://localhost:9000';
    process.env.S3_ACCESS_KEY_ID = 'key';
    process.env.S3_SECRET_ACCESS_KEY = 'secret';

    const moduleRef = await Test.createTestingModule({
      imports: [
        ConfigModule.forRoot({
          isGlobal: true,
          ignoreEnvFile: true,
          load: [storageConfig],
        }),
        StorageModule,
      ],
    }).compile();

    const internal = moduleRef.get<S3Client>(S3_CLIENT);
    const presign = moduleRef.get<S3Client>(S3_PRESIGN_CLIENT);
    const internalEndpoint = await internal.config.endpoint!();
    const publicEndpoint = await presign.config.endpoint!();

    expect(moduleRef.get(StorageService)).toBeInstanceOf(StorageService);
    expect(internalEndpoint.hostname).toBe('minio');
    expect(publicEndpoint.hostname).toBe('localhost');
    expect(internal.config.forcePathStyle).toBe(true);
  });
});
