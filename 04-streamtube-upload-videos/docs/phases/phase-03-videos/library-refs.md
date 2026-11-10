---
libs:
  bullmq:
    version: "~5.81.5"
    context7_id: "/taskforcesh/bullmq"
    fetched_at: "2026-11-09T23:40:00-03:00"
  "@nestjs/bullmq":
    version: "^11.0.5"
    context7_id: "/nestjs/docs.nestjs.com"
    fetched_at: "2026-11-09T23:40:00-03:00"
  "@aws-sdk/client-s3":
    version: "~3.1156.0"
    context7_id: "/websites/aws_amazon_awsjavascriptsdk_v3"
    fetched_at: "2026-11-09T23:40:00-03:00"
  "@aws-sdk/s3-request-presigner":
    version: "~3.1156.0"
    context7_id: "/aws/aws-sdk-js-v3"
    fetched_at: "2026-11-09T23:40:00-03:00"
sources_mtime:
  docs/decisions/technical-decisions-phase-03-videos.md: "2026-11-09T23:39:33-03:00"
---

# phase-03-videos — Library References

Distilled docs for the libraries decided in this phase.

**Note on the source.** During planning and implementation the context7 MCP server was not configured in this workspace (`.mcp.json` lists only `postgres`), so the official documentation pages and changelogs were consulted directly, and versions/peer ranges were read from the npm registry (`npm view`) inside the `nestjs-api` container. After the implementation, the APIs below were re-checked against context7 through its HTTP API (`context7.com/api/v1`, library IDs in the front matter):

- **Confirmed in context7:** BullMQ `attempts` + exponential `backoff`, `UnrecoverableError`, custom `jobId`, `removeOnComplete`/`removeOnFail`, `attemptsMade`; NestJS `BullModule.forRootAsync`, `registerQueue`, `@InjectQueue`, `@Processor` + `WorkerHost` with dispatch by `job.name`; AWS SDK v3 `CreateMultipartUpload`/`UploadPart`/`CompleteMultipartUpload`/`AbortMultipartUpload`/`HeadObject`/`PutObject`/`DeleteObject` commands and `getSignedUrl(..., { expiresIn })`.
- **Not found in the context7 snippets** (confirmed only in the installed SDK typings, `@aws-sdk/client-s3/dist-types`, and exercised by the e2e tests against MinIO): `forcePathStyle`, `requestChecksumCalculation` / `responseChecksumValidation: 'WHEN_REQUIRED'`.
- No divergence was found between context7 and what had been implemented.

## bullmq

**Version decision:** `~5.81.5` (latest 5.x: 5.81.5, 2026-09-10). The 6.0.0 major (2026-07-30) lists breaking changes — `Connection` constructor parameter replaced by `BackendFactory`, `Queue#client`/`Worker#blockingClient` removed, `ioredis` turned into an optional peer that must be installed explicitly, `Job#discard()` removed in favour of `UnrecoverableError`. The 5.x line is the one the NestJS recipe documents and avoids the extra peer.

APIs used in this phase:

```typescript
import { Job, Queue, UnrecoverableError } from 'bullmq';

await queue.add('process-video', { videoId }, {
  jobId: videoId,                       // dedup: one active job per video
  attempts: 3,
  backoff: { type: 'exponential', delay: 5000 },
  removeOnComplete: 1000,
  removeOnFail: 5000,
});

// inside a worker: throwing UnrecoverableError moves the job to failed without retries
throw new UnrecoverableError('File is not a video');

// job.attemptsMade = attempts already finished before the current one;
// job.opts.attempts = configured attempts → last attempt when attemptsMade + 1 >= attempts
```

## @nestjs/bullmq

**Version decision:** `^11.0.5` — peer `bullmq: ^3 || ^4 || ^5 || ^6`, `@nestjs/common|core: ^10 || ^11`.

```typescript
BullModule.forRootAsync({
  inject: [queueConfig.KEY],
  useFactory: (cfg: ConfigType<typeof queueConfig>) => ({
    connection: { host: cfg.host, port: cfg.port },
  }),
});
BullModule.registerQueue({ name: VIDEO_PROCESSING_QUEUE });

constructor(@InjectQueue(VIDEO_PROCESSING_QUEUE) private readonly queue: Queue) {}

@Processor(VIDEO_PROCESSING_QUEUE)
export class VideoProcessor extends WorkerHost {
  async process(job: Job<VideoProcessingJobData>): Promise<void> { /* ... */ }
}
```

- A consumer must be registered as a provider of a module; only the worker process (`WorkerModule`) registers `VideoProcessor`, so the API process is a pure producer.
- BullMQ does not support Bull's `@Process('name')`; dispatch by `job.name` inside `process()` if multiple job names exist.

## @aws-sdk/client-s3

**Version decision:** `~3.1156.0` (2026-10-22).

```typescript
const client = new S3Client({
  region, endpoint, forcePathStyle: true,
  credentials: { accessKeyId, secretAccessKey },
  requestChecksumCalculation: 'WHEN_REQUIRED',   // SDK ≥ 3.729 sends CRC32 by default;
  responseChecksumValidation: 'WHEN_REQUIRED',   // MinIO / presigned part URLs don't expect it
});

CreateMultipartUploadCommand({ Bucket, Key, ContentType })  // → { UploadId }
UploadPartCommand({ Bucket, Key, UploadId, PartNumber })    // presigned, client PUTs bytes
CompleteMultipartUploadCommand({ Bucket, Key, UploadId, MultipartUpload: { Parts: [{ ETag, PartNumber }] } })
AbortMultipartUploadCommand({ Bucket, Key, UploadId })
HeadObjectCommand({ Bucket, Key })                          // → ContentLength, ContentType
PutObjectCommand({ Bucket, Key, Body, ContentType })
DeleteObjectCommand({ Bucket, Key })
GetObjectCommand({ Bucket, Key, ResponseContentDisposition, ResponseContentType })  // presigned
```

- S3 multipart limits: part size 5 MiB–5 GiB (last part may be smaller), max 10,000 parts, single `PUT` max 5 GiB.
- Errors from `CompleteMultipartUpload` with bad input surface as `S3ServiceException` with `name` in `InvalidPart`, `InvalidPartOrder`, `NoSuchUpload`, `EntityTooSmall`.

## @aws-sdk/s3-request-presigner

```typescript
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
const url = await getSignedUrl(presignClient, new UploadPartCommand({ ... }), { expiresIn: 86400 });
```

- Signing is local (HMAC over the canonical request) — no network call, so signing 103 part URLs for a 10GB upload is cheap.
- SigV4 includes the `Host` header: the URL must be signed with the exact endpoint the client will use (`S3_PUBLIC_ENDPOINT`).
- Max `expiresIn` for SigV4 presigned URLs is 7 days.

## FFmpeg / ffprobe (binaries, no npm wrapper)

```
ffprobe -v error -print_format json -show_format -show_streams <url>
ffmpeg -v error -ss <t> -i <url> -frames:v 1 -vf scale=640:-2 -f image2 -c:v mjpeg pipe:1
```

- HTTP inputs are read with range requests (seekable), so `-ss` before `-i` seeks without downloading the whole file.
- Executed via `child_process.spawn(binary, args)` (argument array, no shell).
