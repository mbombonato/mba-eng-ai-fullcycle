import { Injectable } from '@nestjs/common';
import { spawn } from 'node:child_process';
import { NotAVideoFileException } from '../../common/exceptions/domain.exception';
import { THUMBNAIL_WIDTH } from '../videos.constants';
import {
  type FfprobeOutput,
  type ParsedProbe,
  parseProbeOutput,
} from './ffprobe.parser';

const FFPROBE_BIN = 'ffprobe';
const FFMPEG_BIN = 'ffmpeg';
const COMMAND_TIMEOUT_MS = 5 * 60 * 1000;
const INVALID_INPUT_MARKERS = [
  'Invalid data found when processing input',
  'moov atom not found',
];

interface CommandResult {
  stdout: Buffer;
  stderr: string;
}

class MediaCommandError extends Error {
  constructor(
    readonly binary: string,
    readonly exitCode: number | null,
    readonly stderr: string,
  ) {
    super(
      `${binary} exited with code ${exitCode}: ${stderr.trim().slice(0, 500)}`,
    );
    this.name = 'MediaCommandError';
  }
}

/** Thin wrapper over the FFmpeg binaries (argument arrays, no shell). */
@Injectable()
export class FfmpegService {
  /** Reads container/stream metadata. `input` may be a local path or an HTTP(S) URL. */
  async probe(input: string): Promise<ParsedProbe> {
    const { stdout } = await this.run(FFPROBE_BIN, [
      '-v',
      'error',
      '-print_format',
      'json',
      '-show_format',
      '-show_streams',
      input,
    ]);
    let parsed: FfprobeOutput;
    try {
      parsed = JSON.parse(stdout.toString('utf8')) as FfprobeOutput;
    } catch {
      throw new NotAVideoFileException('unreadable probe output');
    }
    return parseProbeOutput(parsed);
  }

  /** Grabs one frame at `atSeconds` as a JPEG scaled to 640px wide. */
  async extractFrame(input: string, atSeconds: number): Promise<Buffer> {
    const { stdout } = await this.run(FFMPEG_BIN, [
      '-v',
      'error',
      '-ss',
      atSeconds.toFixed(3),
      '-i',
      input,
      '-frames:v',
      '1',
      '-vf',
      `scale=${THUMBNAIL_WIDTH}:-2`,
      '-f',
      'image2',
      '-c:v',
      'mjpeg',
      'pipe:1',
    ]);
    if (stdout.length === 0) {
      throw new Error('ffmpeg produced an empty thumbnail');
    }
    return stdout;
  }

  private async run(binary: string, args: string[]): Promise<CommandResult> {
    try {
      return await this.spawnCollect(binary, args);
    } catch (err) {
      if (
        err instanceof MediaCommandError &&
        INVALID_INPUT_MARKERS.some((marker) => err.stderr.includes(marker))
      ) {
        throw new NotAVideoFileException(err.stderr.trim().slice(0, 200));
      }
      throw err;
    }
  }

  private spawnCollect(binary: string, args: string[]): Promise<CommandResult> {
    return new Promise((resolve, reject) => {
      const child = spawn(binary, args, { stdio: ['ignore', 'pipe', 'pipe'] });
      const stdoutChunks: Buffer[] = [];
      let stderr = '';
      const timer = setTimeout(() => {
        child.kill('SIGKILL');
        reject(new Error(`${binary} timed out after ${COMMAND_TIMEOUT_MS}ms`));
      }, COMMAND_TIMEOUT_MS);

      child.stdout.on('data', (chunk: Buffer) => stdoutChunks.push(chunk));
      child.stderr.on('data', (chunk: Buffer) => {
        stderr += chunk.toString('utf8');
      });
      child.on('error', (err) => {
        clearTimeout(timer);
        reject(err);
      });
      child.on('close', (code) => {
        clearTimeout(timer);
        if (code === 0) {
          resolve({ stdout: Buffer.concat(stdoutChunks), stderr });
        } else {
          reject(new MediaCommandError(binary, code, stderr));
        }
      });
    });
  }
}
