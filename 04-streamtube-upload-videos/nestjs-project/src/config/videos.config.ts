import { registerAs } from '@nestjs/config';

const MEBIBYTE = 1024 * 1024;

export default registerAs('videos', () => ({
  uploadPartSizeBytes:
    parseInt(process.env.UPLOAD_PART_SIZE_MB || '100', 10) * MEBIBYTE,
  uploadUrlExpirationSeconds: parseInt(
    process.env.UPLOAD_URL_EXPIRATION_SECONDS || '86400',
    10,
  ),
  streamUrlExpirationSeconds: parseInt(
    process.env.STREAM_URL_EXPIRATION_SECONDS || '3600',
    10,
  ),
  processingAttempts: parseInt(
    process.env.VIDEO_PROCESSING_ATTEMPTS || '3',
    10,
  ),
}));
