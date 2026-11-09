import { randomUUID } from 'node:crypto';
import { DataSource } from 'typeorm';
import { Channel } from '../channels/entities/channel.entity';
import { User } from '../users/entities/user.entity';
import { Video } from '../videos/entities/video.entity';
import { generateVideoSlug } from '../videos/slug.util';
import { VideoStatus, videoSourceKey } from '../videos/videos.constants';

let sequence = 0;

export async function createUserWithChannel(
  dataSource: DataSource,
): Promise<{ user: User; channel: Channel }> {
  const suffix = `${Date.now()}_${++sequence}`;
  const user = await dataSource.getRepository(User).save({
    email: `video_owner_${suffix}@example.com`,
    password: 'hashed',
    is_confirmed: true,
  });
  const channel = await dataSource.getRepository(Channel).save({
    name: `owner_${suffix}`,
    nickname: `owner_${suffix}`.slice(0, 50),
    user_id: user.id,
  });
  return { user, channel };
}

export function buildVideo(
  channelId: string,
  overrides: Partial<Video> = {},
): Partial<Video> {
  const id = overrides.id ?? randomUUID();
  return {
    id,
    channel_id: channelId,
    title: 'My trip to the mountains',
    slug: generateVideoSlug(),
    status: VideoStatus.DRAFT,
    original_file_name: 'trip.mp4',
    mime_type: 'video/mp4',
    file_size: 1024,
    video_key: videoSourceKey(id),
    upload_id: 'upload-id',
    ...overrides,
  };
}
