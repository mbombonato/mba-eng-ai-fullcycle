import { Matches } from 'class-validator';
import { VIDEO_SLUG_PATTERN } from '../videos.constants';

export class VideoSlugParamDto {
  /** Unique public id of the video (11 URL-safe characters). */
  @Matches(VIDEO_SLUG_PATTERN, { message: 'slug must be a valid video slug' })
  slug: string;
}
