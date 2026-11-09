import { DataSource, QueryFailedError, Repository } from 'typeorm';
import { RefreshToken } from '../../auth/entities/refresh-token.entity';
import { VerificationToken } from '../../auth/entities/verification-token.entity';
import { Channel } from '../../channels/entities/channel.entity';
import {
  cleanAllTables,
  createTestDataSource,
} from '../../test/create-test-data-source';
import { buildVideo, createUserWithChannel } from '../../test/video-factories';
import { User } from '../../users/entities/user.entity';
import { VIDEO_MAX_FILE_SIZE_BYTES, VideoStatus } from '../videos.constants';
import { Video } from './video.entity';

const ALL_ENTITIES = [User, Channel, RefreshToken, VerificationToken, Video];

describe('Video entity (integration)', () => {
  let dataSource: DataSource;
  let videoRepository: Repository<Video>;

  beforeAll(async () => {
    dataSource = createTestDataSource(ALL_ENTITIES);
    await dataSource.initialize();
    videoRepository = dataSource.getRepository(Video);
  });

  afterAll(async () => {
    await dataSource.destroy();
  });

  beforeEach(async () => {
    await cleanAllTables(dataSource);
  });

  it('should default status to draft and keep nullable processing fields empty', async () => {
    const { channel } = await createUserWithChannel(dataSource);
    const video = buildVideo(channel.id);
    delete video.status;

    const saved = await videoRepository.save(video);
    const found = await videoRepository.findOneByOrFail({ id: saved.id });

    expect(found.status).toBe(VideoStatus.DRAFT);
    expect(found.thumbnail_key).toBeNull();
    expect(found.duration_seconds).toBeNull();
    expect(found.metadata).toBeNull();
    expect(found.processed_at).toBeNull();
  });

  it('should round-trip a 10 GiB bigint file_size as a number', async () => {
    const { channel } = await createUserWithChannel(dataSource);
    const saved = await videoRepository.save(
      buildVideo(channel.id, { file_size: VIDEO_MAX_FILE_SIZE_BYTES }),
    );

    const found = await videoRepository.findOneByOrFail({ id: saved.id });

    expect(found.file_size).toBe(10_737_418_240);
    expect(typeof found.file_size).toBe('number');
  });

  it('should persist metadata as jsonb', async () => {
    const { channel } = await createUserWithChannel(dataSource);
    const metadata = {
      format_name: 'mov,mp4,m4a,3gp,3g2,mj2',
      bit_rate: 1200000,
      width: 1920,
      height: 1080,
      video_codec: 'h264',
      audio_codec: 'aac',
      frame_rate: 30,
    };
    const saved = await videoRepository.save(
      buildVideo(channel.id, { metadata, duration_seconds: 12.5 }),
    );

    const found = await videoRepository.findOneByOrFail({ id: saved.id });

    expect(found.metadata).toEqual(metadata);
    expect(found.duration_seconds).toBe(12.5);
  });

  it('should enforce a unique slug', async () => {
    const { channel } = await createUserWithChannel(dataSource);
    await videoRepository.save(buildVideo(channel.id, { slug: 'AAAAAAAAAAA' }));

    await expect(
      videoRepository.save(buildVideo(channel.id, { slug: 'AAAAAAAAAAA' })),
    ).rejects.toBeInstanceOf(QueryFailedError);
  });

  it('should load the owning channel and its inverse videos relation', async () => {
    const { channel } = await createUserWithChannel(dataSource);
    const saved = await videoRepository.save(buildVideo(channel.id));

    const video = await videoRepository.findOneOrFail({
      where: { id: saved.id },
      relations: { channel: true },
    });
    const withVideos = await dataSource.getRepository(Channel).findOneOrFail({
      where: { id: channel.id },
      relations: { videos: true },
    });

    expect(video.channel.id).toBe(channel.id);
    expect(withVideos.videos.map((v) => v.id)).toEqual([saved.id]);
  });

  it('should cascade delete videos when the channel is deleted', async () => {
    const { channel } = await createUserWithChannel(dataSource);
    const saved = await videoRepository.save(buildVideo(channel.id));

    await dataSource.getRepository(Channel).delete({ id: channel.id });

    expect(await videoRepository.findOneBy({ id: saved.id })).toBeNull();
  });
});
