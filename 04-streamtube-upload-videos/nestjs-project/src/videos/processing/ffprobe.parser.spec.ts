import { NotAVideoFileException } from '../../common/exceptions/domain.exception';
import { parseFrameRate, parseProbeOutput } from './ffprobe.parser';

describe('parseProbeOutput', () => {
  it('should map duration and metadata from format and streams', () => {
    const result = parseProbeOutput({
      format: {
        format_name: 'mov,mp4,m4a,3gp,3g2,mj2',
        duration: '12.480000',
        bit_rate: '1250000',
      },
      streams: [
        {
          codec_type: 'video',
          codec_name: 'h264',
          width: 1920,
          height: 1080,
          avg_frame_rate: '30000/1001',
        },
        { codec_type: 'audio', codec_name: 'aac' },
      ],
    });

    expect(result).toEqual({
      durationSeconds: 12.48,
      metadata: {
        format_name: 'mov,mp4,m4a,3gp,3g2,mj2',
        bit_rate: 1250000,
        width: 1920,
        height: 1080,
        video_codec: 'h264',
        audio_codec: 'aac',
        frame_rate: 29.97,
      },
    });
  });

  it('should fall back to the stream duration and accept videos without audio', () => {
    const result = parseProbeOutput({
      format: { format_name: 'webm' },
      streams: [
        {
          codec_type: 'video',
          codec_name: 'vp9',
          duration: '3.5',
          avg_frame_rate: '0/0',
          r_frame_rate: '25/1',
        },
      ],
    });

    expect(result.durationSeconds).toBe(3.5);
    expect(result.metadata.audio_codec).toBeNull();
    expect(result.metadata.bit_rate).toBeNull();
    expect(result.metadata.frame_rate).toBe(25);
  });

  it('should reject audio-only files', () => {
    expect(() =>
      parseProbeOutput({
        format: { format_name: 'mp3', duration: '10' },
        streams: [{ codec_type: 'audio', codec_name: 'mp3' }],
      }),
    ).toThrow(NotAVideoFileException);
  });

  it('should reject outputs without streams', () => {
    expect(() => parseProbeOutput({})).toThrow(NotAVideoFileException);
  });
});

describe('parseFrameRate', () => {
  it.each([
    ['25/1', 25],
    ['30000/1001', 29.97],
    ['0/0', null],
    [undefined, null],
    ['garbage', null],
  ])('should parse %s as %s', (input, expected) => {
    expect(parseFrameRate(input)).toBe(expected);
  });
});
