import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

/** Temporary directory for generated media; call `cleanup()` in afterAll. */
export function createMediaDir(): { dir: string; cleanup: () => void } {
  const dir = mkdtempSync(join(tmpdir(), 'streamtube-media-'));
  return { dir, cleanup: () => rmSync(dir, { recursive: true, force: true }) };
}

/**
 * Generates a small H.264/AAC MP4 with FFmpeg's synthetic sources, so tests
 * exercise the real binaries without committing binary fixtures.
 */
export function generateTestVideo(
  dir: string,
  {
    seconds = 2,
    name = 'sample.mp4',
  }: { seconds?: number; name?: string } = {},
): string {
  const output = join(dir, name);
  execFileSync('ffmpeg', [
    '-v',
    'error',
    '-y',
    '-f',
    'lavfi',
    '-i',
    `testsrc=duration=${seconds}:size=320x240:rate=25`,
    '-f',
    'lavfi',
    '-i',
    `sine=frequency=440:duration=${seconds}`,
    '-c:v',
    'libx264',
    '-pix_fmt',
    'yuv420p',
    '-c:a',
    'aac',
    '-shortest',
    '-movflags',
    '+faststart',
    output,
  ]);
  return output;
}

export function writeNotAVideo(dir: string, name = 'notes.mp4'): string {
  const output = join(dir, name);
  writeFileSync(output, 'this is plain text pretending to be a video\n');
  return output;
}

export const JPEG_MAGIC = Buffer.from([0xff, 0xd8, 0xff]);
