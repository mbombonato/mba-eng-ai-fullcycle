import { NotAVideoFileException } from '../../common/exceptions/domain.exception';
import {
  createMediaDir,
  generateTestVideo,
  JPEG_MAGIC,
  writeNotAVideo,
} from '../../test/media';
import { FfmpegService } from './ffmpeg.service';

describe('FfmpegService (integration — real ffmpeg/ffprobe)', () => {
  const service = new FfmpegService();
  const media = createMediaDir();
  let videoPath: string;

  beforeAll(() => {
    videoPath = generateTestVideo(media.dir, { seconds: 2 });
  });

  afterAll(() => media.cleanup());

  it('should probe duration, dimensions and codecs', async () => {
    const result = await service.probe(videoPath);

    expect(result.durationSeconds).toBeGreaterThan(1.9);
    expect(result.durationSeconds).toBeLessThan(2.2);
    expect(result.metadata).toMatchObject({
      width: 320,
      height: 240,
      video_codec: 'h264',
      audio_codec: 'aac',
      frame_rate: 25,
    });
    expect(result.metadata.format_name).toContain('mp4');
  });

  it('should throw NotAVideoFileException for a text file', async () => {
    await expect(
      service.probe(writeNotAVideo(media.dir)),
    ).rejects.toBeInstanceOf(NotAVideoFileException);
  });

  it('should extract a JPEG frame', async () => {
    const frame = await service.extractFrame(videoPath, 1);

    expect(frame.subarray(0, 3)).toEqual(JPEG_MAGIC);
    expect(frame.length).toBeGreaterThan(1000);
  });

  it('should fail with a regular error for a missing input', async () => {
    await expect(
      service.probe(`${media.dir}/does-not-exist.mp4`),
    ).rejects.toThrow(/ffprobe exited with code/);
  });
});
