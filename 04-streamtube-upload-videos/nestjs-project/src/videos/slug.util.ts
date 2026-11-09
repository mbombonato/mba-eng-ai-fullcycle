import { randomBytes } from 'node:crypto';
import { VIDEO_SLUG_BYTES } from './videos.constants';

/** Random, URL-safe, non-enumerable public id (11 chars, 64 bits of entropy). */
export function generateVideoSlug(): string {
  return randomBytes(VIDEO_SLUG_BYTES).toString('base64url');
}
