export enum VideoStatus {
  DRAFT = 'draft',
  PROCESSING = 'processing',
  READY = 'ready',
  FAILED = 'failed',
}

/** Business limit of the platform: 10 GiB per uploaded video. */
export const VIDEO_MAX_FILE_SIZE_BYTES = 10 * 1024 ** 3;

/** 8 random bytes encoded as base64url → 11 characters. */
export const VIDEO_SLUG_BYTES = 8;
export const VIDEO_SLUG_LENGTH = 11;
export const VIDEO_SLUG_PATTERN = /^[A-Za-z0-9_-]{11}$/;
export const VIDEO_SLUG_MAX_ATTEMPTS = 5;

export const VIDEO_CONTENT_TYPE_PATTERN = /^video\/[a-z0-9.+-]+$/i;

export const VIDEO_PROCESSING_QUEUE = 'video-processing';
export const PROCESS_VIDEO_JOB = 'process-video';
export const PROCESS_VIDEO_BACKOFF_MS = 5000;
export const PROCESS_VIDEO_REMOVE_ON_COMPLETE = 1000;
export const PROCESS_VIDEO_REMOVE_ON_FAIL = 5000;

export const THUMBNAIL_CONTENT_TYPE = 'image/jpeg';
export const THUMBNAIL_WIDTH = 640;
export const THUMBNAIL_MAX_OFFSET_SECONDS = 1;

/** Presigned internal URL lifetime for the worker's FFmpeg input. */
export const PROCESSING_SOURCE_URL_EXPIRATION_SECONDS = 3600;

export const FAILURE_REASON_MAX_LENGTH = 1000;

export const videoSourceKey = (videoId: string): string =>
  `videos/${videoId}/source`;

export const videoThumbnailKey = (videoId: string): string =>
  `videos/${videoId}/thumbnail.jpg`;
