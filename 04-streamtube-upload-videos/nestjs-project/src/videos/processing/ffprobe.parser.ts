import { NotAVideoFileException } from '../../common/exceptions/domain.exception';
import type { VideoMetadata } from '../videos.types';

interface FfprobeStream {
  codec_type?: string;
  codec_name?: string;
  width?: number;
  height?: number;
  avg_frame_rate?: string;
  r_frame_rate?: string;
  duration?: string;
}

interface FfprobeFormat {
  format_name?: string;
  duration?: string;
  bit_rate?: string;
}

export interface FfprobeOutput {
  streams?: FfprobeStream[];
  format?: FfprobeFormat;
}

export interface ParsedProbe {
  durationSeconds: number | null;
  metadata: VideoMetadata;
}

function toNumber(value: string | number | undefined): number | null {
  if (value === undefined || value === null || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/** "30000/1001" → 29.97 (2 decimals); "0/0" → null. */
export function parseFrameRate(rate: string | undefined): number | null {
  if (!rate) return null;
  const [num, den] = rate.split('/').map(Number);
  if (
    !Number.isFinite(num) ||
    !Number.isFinite(den) ||
    den === 0 ||
    num === 0
  ) {
    return null;
  }
  return Math.round((num / den) * 100) / 100;
}

export function parseProbeOutput(output: FfprobeOutput): ParsedProbe {
  const streams = output.streams ?? [];
  const video = streams.find((s) => s.codec_type === 'video');
  if (!video) {
    throw new NotAVideoFileException('no video stream found');
  }
  const audio = streams.find((s) => s.codec_type === 'audio');
  const format = output.format ?? {};

  return {
    durationSeconds: toNumber(format.duration) ?? toNumber(video.duration),
    metadata: {
      format_name: format.format_name ?? null,
      bit_rate: toNumber(format.bit_rate),
      width: video.width ?? null,
      height: video.height ?? null,
      video_codec: video.codec_name ?? null,
      audio_codec: audio?.codec_name ?? null,
      frame_rate:
        parseFrameRate(video.avg_frame_rate) ??
        parseFrameRate(video.r_frame_rate),
    },
  };
}
