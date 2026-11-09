import { BullModule } from '@nestjs/bullmq';
import { ConfigModule } from '@nestjs/config';
import type { ModuleMetadata } from '@nestjs/common';
import { Test, TestingModule } from '@nestjs/testing';
import { TypeOrmModule } from '@nestjs/typeorm';
import { RefreshToken } from '../auth/entities/refresh-token.entity';
import { VerificationToken } from '../auth/entities/verification-token.entity';
import { Channel } from '../channels/entities/channel.entity';
import { configModuleOptions } from '../config/config-module.options';
import { bullRootAsyncOptions } from '../queue/bull-root.options';
import { User } from '../users/entities/user.entity';
import { Video } from '../videos/entities/video.entity';
import { createTestDataSource } from './create-test-data-source';
import { signPresignedUrlsWithInternalEndpoint } from './storage';

export const ALL_ENTITIES = [
  User,
  Channel,
  RefreshToken,
  VerificationToken,
  Video,
];

/**
 * Real infrastructure for video integration tests: Postgres (`db`),
 * MinIO (`minio`) and Redis (`redis`) from the Compose network.
 */
export async function createVideosTestingModule(
  imports: NonNullable<ModuleMetadata['imports']>,
  providers: NonNullable<ModuleMetadata['providers']> = [],
): Promise<TestingModule> {
  signPresignedUrlsWithInternalEndpoint();
  return Test.createTestingModule({
    imports: [
      ConfigModule.forRoot(configModuleOptions),
      TypeOrmModule.forRoot({
        ...createTestDataSource(ALL_ENTITIES).options,
        synchronize: false,
      }),
      BullModule.forRootAsync(bullRootAsyncOptions),
      ...imports,
    ],
    providers,
  }).compile();
}
