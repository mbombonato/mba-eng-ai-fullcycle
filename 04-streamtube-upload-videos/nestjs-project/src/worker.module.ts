import { BullModule } from '@nestjs/bullmq';
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { configModuleOptions } from './config/config-module.options';
import { typeOrmAsyncOptions } from './database/typeorm-options.factory';
import { bullRootAsyncOptions } from './queue/bull-root.options';
import { UsersModule } from './users/users.module';
import { VideoProcessingModule } from './videos/processing/video-processing.module';

/** Root module of the video worker process (no HTTP server). */
@Module({
  imports: [
    ConfigModule.forRoot(configModuleOptions),
    TypeOrmModule.forRootAsync(typeOrmAsyncOptions),
    BullModule.forRootAsync(bullRootAsyncOptions),
    // Registers the User entity: autoLoadEntities only knows entities from
    // forFeature(), and Video → Channel → User must be fully resolvable.
    UsersModule,
    VideoProcessingModule,
  ],
})
export class WorkerModule {}
