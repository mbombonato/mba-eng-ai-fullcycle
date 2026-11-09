import { Transform } from 'class-transformer';
import {
  IsInt,
  IsNotEmpty,
  IsString,
  Matches,
  Max,
  MaxLength,
  Min,
} from 'class-validator';
import {
  VIDEO_CONTENT_TYPE_PATTERN,
  VIDEO_MAX_FILE_SIZE_BYTES,
} from '../videos.constants';

export class CreateVideoDto {
  /** Initial title of the video (editable later). */
  @Transform(({ value }: { value: unknown }) =>
    typeof value === 'string' ? value.trim() : value,
  )
  @IsString()
  @IsNotEmpty()
  @MaxLength(100)
  title: string;

  /** Original file name, used as the download file name. */
  @IsString()
  @IsNotEmpty()
  @MaxLength(255)
  file_name: string;

  /** File size in bytes (max 10 GiB = 10737418240). */
  @IsInt()
  @Min(1)
  @Max(VIDEO_MAX_FILE_SIZE_BYTES)
  file_size: number;

  /** MIME type of the file — must be `video/*` (e.g. `video/mp4`). */
  @IsString()
  @Matches(VIDEO_CONTENT_TYPE_PATTERN, {
    message: 'content_type must be a video MIME type',
  })
  content_type: string;
}
