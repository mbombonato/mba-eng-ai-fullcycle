import { ApiProperty } from '@nestjs/swagger';
import { Video } from '../entities/video.entity';
import { VideoStatus } from '../videos.constants';

export class VideoMetadataDto {
  @ApiProperty({ nullable: true, example: 'mov,mp4,m4a,3gp,3g2,mj2' })
  format_name: string | null;

  @ApiProperty({ nullable: true, example: 1250000 })
  bit_rate: number | null;

  @ApiProperty({ nullable: true, example: 1920 })
  width: number | null;

  @ApiProperty({ nullable: true, example: 1080 })
  height: number | null;

  @ApiProperty({ nullable: true, example: 'h264' })
  video_codec: string | null;

  @ApiProperty({ nullable: true, example: 'aac' })
  audio_codec: string | null;

  @ApiProperty({ nullable: true, example: 29.97 })
  frame_rate: number | null;
}

export class VideoResponseDto {
  @ApiProperty({ format: 'uuid' })
  id: string;

  @ApiProperty({
    example: 'dQw4w9WgXcQ',
    description: 'Unique public id used in URLs',
  })
  slug: string;

  @ApiProperty({ example: 'My trip to the mountains' })
  title: string;

  @ApiProperty({ enum: VideoStatus, enumName: 'VideoStatus' })
  status: VideoStatus;

  @ApiProperty({ format: 'uuid' })
  channel_id: string;

  @ApiProperty({ example: 'trip.mp4' })
  original_file_name: string;

  @ApiProperty({ example: 'video/mp4' })
  mime_type: string;

  @ApiProperty({ example: 104857600, description: 'Size in bytes' })
  file_size: number;

  @ApiProperty({ nullable: true, example: 125.4 })
  duration_seconds: number | null;

  @ApiProperty({ type: VideoMetadataDto, nullable: true })
  metadata: VideoMetadataDto | null;

  @ApiProperty({ nullable: true })
  failure_reason: string | null;

  @ApiProperty({ nullable: true, type: String, format: 'date-time' })
  processed_at: Date | null;

  @ApiProperty({ type: String, format: 'date-time' })
  created_at: Date;

  @ApiProperty({ type: String, format: 'date-time' })
  updated_at: Date;

  static fromEntity(video: Video): VideoResponseDto {
    const dto = new VideoResponseDto();
    dto.id = video.id;
    dto.slug = video.slug;
    dto.title = video.title;
    dto.status = video.status;
    dto.channel_id = video.channel_id;
    dto.original_file_name = video.original_file_name;
    dto.mime_type = video.mime_type;
    dto.file_size = video.file_size;
    dto.duration_seconds = video.duration_seconds;
    dto.metadata = video.metadata;
    dto.failure_reason = video.failure_reason;
    dto.processed_at = video.processed_at;
    dto.created_at = video.created_at;
    dto.updated_at = video.updated_at;
    return dto;
  }
}
