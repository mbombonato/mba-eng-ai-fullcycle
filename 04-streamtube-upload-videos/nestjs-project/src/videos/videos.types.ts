export interface VideoMetadata {
  format_name: string | null;
  bit_rate: number | null;
  width: number | null;
  height: number | null;
  video_codec: string | null;
  audio_codec: string | null;
  frame_rate: number | null;
}

export interface VideoProcessingJobData {
  videoId: string;
}

export interface ProcessedVideoResult {
  durationSeconds: number | null;
  metadata: VideoMetadata;
  thumbnailKey: string;
}
