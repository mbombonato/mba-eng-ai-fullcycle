import { Module } from '@nestjs/common';
import { StorageModule } from '../../storage/storage.module';
import { VideosModule } from '../videos.module';
import { FfmpegService } from './ffmpeg.service';
import { VideoProcessingService } from './video-processing.service';
import { VideoProcessor } from './video.processor';

/** Worker-side module: the queue consumer and the FFmpeg pipeline. */
@Module({
  imports: [VideosModule, StorageModule],
  providers: [VideoProcessor, VideoProcessingService, FfmpegService],
})
export class VideoProcessingModule {}
