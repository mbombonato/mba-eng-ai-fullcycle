---
kind: phase
name: phase-03-videos
sources_mtime:
  docs/project-plan.md: "2026-11-09T16:25:30-03:00"
  docs/decisions/technical-decisions-phase-03-videos.md: "2026-11-09T23:39:33-03:00"
  docs/phases/phase-03-videos/context.md: "2026-11-09T23:54:52-03:00"
  docs/phases/phase-03-videos/validation.md: "2026-11-09T16:47:00-03:00"
  docs/phases/phase-03-videos/library-refs.md: "2026-11-09T16:45:00-03:00"
---

# Phase 03 — Upload e Processamento de Vídeos

## Objective

Deliver video upload of up to 10GB directly to object storage (S3 multipart via presigned URLs, never through the API), automatic draft pre-registration, asynchronous processing by a dedicated FFmpeg worker fed by a BullMQ/Redis queue (duration, metadata and thumbnail extraction), a unique short URL per video, and streaming (HTTP range / `206 Partial Content`) plus download of the original file — with MinIO, Redis and the worker running in Docker Compose next to the API.

---

## Step Implementations

### SI-03.1 — Dependencies, Configuration Namespaces, and Compose Infrastructure

**Description:** Install the Phase 03 libraries, add the `storage`, `queue` and `videos` config namespaces, install FFmpeg in the dev image and add MinIO (+ bucket init), Redis and the worker service to Compose. (`phase-03-videos/TD-01`, `TD-03`, `TD-04`)

**Technical actions:**

- Install in nestjs-project: `bullmq@~5.81.5`, `@nestjs/bullmq@^11.0.5`, `@aws-sdk/client-s3@~3.1156.0`, `@aws-sdk/s3-request-presigner@~3.1156.0`
- `Dockerfile.dev`: add `ffmpeg` to the `apt install` line (shared by `nestjs-api` and `worker`)
- Create `src/config/storage.config.ts` — `registerAs('storage')`: `S3_ENDPOINT` (default `http://minio:9000`), `S3_PUBLIC_ENDPOINT` (default `http://localhost:9000`), `S3_REGION` (default `us-east-1`), `S3_ACCESS_KEY_ID` (required), `S3_SECRET_ACCESS_KEY` (required), `S3_BUCKET` (default `streamtube`), `S3_FORCE_PATH_STYLE` (default `true`)
- Create `src/config/queue.config.ts` — `registerAs('queue')`: `REDIS_HOST` (default `redis`), `REDIS_PORT` (default `6379`)
- Create `src/config/videos.config.ts` — `registerAs('videos')`: `UPLOAD_PART_SIZE_MB` (default `100`, min 5, max 5120), `UPLOAD_URL_EXPIRATION_SECONDS` (default `86400`, max `604800`), `STREAM_URL_EXPIRATION_SECONDS` (default `3600`), `VIDEO_PROCESSING_ATTEMPTS` (default `3`)
- Extend `src/config/env.validation.ts` and `.env.example` with all new variables
- `compose.yaml`: add `minio` (`pgsty/minio:RELEASE.2026-08-04T00-00-00Z`, `server /data --console-address :9001`, ports 9000/9001, volume `minio-data`, healthcheck `curl -f http://localhost:9000/minio/health/live`), `minio-init` (same image, entrypoint `sh -c`, `mc alias set` + `mc mb --ignore-existing local/$S3_BUCKET`, depends on `minio` healthy), `redis` (`redis:7.4-alpine`, `--appendonly yes`, port 6379, healthcheck `redis-cli ping`, volume `redis-data`), `worker` (same build as `nestjs-api`, `command: npm run start:worker`, `restart: unless-stopped`, depends on `db`/`redis`/`minio`); `nestjs-api` additionally depends on `redis` and `minio`
- `package.json` scripts: `start:worker` (`ts-node src/worker.ts`), `start:worker:prod` (`node dist/worker`)

**Dependencies:** None

**Acceptance criteria:**

- `docker compose up -d` brings up `nestjs-api`, `db`, `mailpit`, `minio`, `redis`, `worker`; `minio-init` exits 0 after creating the bucket
- `docker compose exec nestjs-api ffprobe -version` succeeds
- Starting the app without `S3_ACCESS_KEY_ID` fails Joi validation
- Existing test suites stay green

**Tests:**

| File | Layer | Verifies |
|------|-------|----------|
| `src/config/env.validation.integration-spec.ts` | Integration | New required storage credentials are enforced; defaults applied for queue/videos vars |

---

### SI-03.2 — Storage Module (S3/MinIO)

**Description:** Encapsulate every object-storage operation in `StorageService` with two S3 clients (internal + presign). (`phase-03-videos/TD-02`, `TD-03`, `TD-06`)

**Technical actions:**

- `src/storage/storage.constants.ts` — DI tokens `S3_CLIENT`, `S3_PRESIGN_CLIENT`
- `src/storage/storage.module.ts` — factory providers building `S3Client` from `storageConfig` (`endpoint` vs `publicEndpoint`, `forcePathStyle`, `requestChecksumCalculation`/`responseChecksumValidation: 'WHEN_REQUIRED'`); exports `StorageService`
- `src/storage/storage.service.ts` — `createMultipartUpload(key, contentType)`, `presignUploadParts(key, uploadId, partCount, expiresIn)`, `completeMultipartUpload(key, uploadId, parts)` (maps S3 `InvalidPart`/`InvalidPartOrder`/`NoSuchUpload`/`EntityTooSmall` to `InvalidUploadPartsException`), `abortMultipartUpload`, `headObject(key)` → `{ size, contentType }`, `putObject(key, body, contentType)`, `deleteObject(key)`, `presignDownloadUrl(key, { expiresIn, contentType?, downloadFileName? })` (public endpoint), `presignInternalDownloadUrl(key, expiresIn)` (internal endpoint — used by the worker)

**Dependencies:** SI-03.1

**Acceptance criteria:**

- A two-part multipart upload (5 MiB + tail) through presigned URLs completes and `headObject` reports the exact size
- Completing with a wrong ETag raises `InvalidUploadPartsException`
- A presigned download URL answers a `Range: bytes=0-9` request with `206` and 10 bytes

**Tests:**

| File | Layer | Verifies |
|------|-------|----------|
| `src/storage/storage.service.integration-spec.ts` | Integration | Multipart lifecycle against real MinIO, invalid parts mapping, put/head/delete, ranged GET 206 via presigned URL, download disposition |
| `src/storage/storage.module.spec.ts` | Unit | Module resolves `StorageService` with both clients from config |

---

### SI-03.3 — Video Entity, Channel Relation, and Migration

**Description:** Create the `videos` table owned by a channel. (`phase-03-videos/TD-05`, `TD-07`)

**Technical actions:**

- `src/videos/videos.constants.ts` — `VideoStatus` enum (`draft`, `processing`, `ready`, `failed`), `VIDEO_MAX_FILE_SIZE_BYTES = 10 * 1024 ** 3`, `VIDEO_SLUG_LENGTH = 11`, queue/job names, storage key builders
- `src/videos/entities/video.entity.ts` — see Data Model; `@ManyToOne(() => Channel, (c) => c.videos, { onDelete: 'CASCADE' })`
- `src/channels/entities/channel.entity.ts` — add inverse `@OneToMany(() => Video, (v) => v.channel) videos`
- Generate `src/database/migrations/<ts>-CreateVideos.ts` with the TypeORM CLI
- Test helpers: add `Video` to every `ALL_ENTITIES`, `DELETE FROM "videos"` first in `cleanAllTables`, add the new migration and table to `migrations.integration-spec.ts` (which must also drop the enum types and run the drops sequentially — otherwise re-running migrations on an already-migrated DB fails with `type ... already exists`)

**Dependencies:** SI-03.1

**Acceptance criteria:**

- `npm run migration:run` creates `videos` and the `videos_status_enum` type; `migration:revert` drops them
- Inserting two videos with the same slug violates the unique index; deleting a channel cascades to its videos

**Tests:**

| File | Layer | Verifies |
|------|-------|----------|
| `src/videos/entities/video.entity.integration-spec.ts` | Integration | Defaults (`status = draft`), unique slug, bigint `file_size` round-trip as number, jsonb metadata, cascade on channel delete |
| `src/database/migrations.integration-spec.ts` | Integration | Three migrations apply and revert; `videos` table managed |

---

### SI-03.4 — Optional Authentication on Public Routes

**Description:** Let `@Public()` handlers know the caller when a valid bearer token is sent. (`phase-03-videos/TD-08`)

**Technical actions:**

- `src/auth/guards/jwt-auth.guard.ts` — on `@Public()` routes, if the header starts with `Bearer `, try `verifyAsync`; on success set `request.user`, on failure ignore; always return `true`. Protected routes unchanged

**Dependencies:** None

**Acceptance criteria:**

- Public route + valid token → `request.user` populated; public route + invalid token → allowed, `request.user` undefined; protected route behaviour unchanged

**Tests:**

| File | Layer | Verifies |
|------|-------|----------|
| `src/auth/guards/jwt-auth.guard.spec.ts` | Unit | New optional-auth branches + existing protected-route cases |

---

### SI-03.5 — Upload Initiation with Draft Pre-Registration (`POST /videos`)

**Description:** Validate the upload request, open the multipart upload, pre-register the video as `draft` with a unique slug, and return presigned part URLs. (`phase-03-videos/TD-02`, `TD-05`, `TD-07`)

**Technical actions:**

- `src/videos/slug.util.ts` — `generateVideoSlug()` = `randomBytes(8).toString('base64url')`
- `src/channels/channels.service.ts` — add `findByUserId(userId)`
- `src/common/exceptions/domain.exception.ts` — add `ChannelNotFoundException`, `VideoNotFoundException`, `InvalidVideoStatusException`, `InvalidUploadPartsException`, `UploadSizeExceededException`, `VideoNotReadyException`, `ThumbnailNotAvailableException`, `NotAVideoFileException`
- `src/videos/dto/create-video.dto.ts`, `src/videos/dto/video-response.dto.ts`, `src/videos/dto/create-video-response.dto.ts`, `src/videos/dto/video-slug-param.dto.ts`
- `src/videos/videos.service.ts` — `createUpload(userId, dto)`: resolve channel → `randomUUID()` id → `createMultipartUpload(videos/{id}/source)` → insert draft with slug retry on unique violation (max 5) → on insert failure abort the multipart upload (compensation) → presign `ceil(file_size / part_size)` part URLs
- `src/videos/videos.controller.ts` — `POST /videos` (authenticated), `@SkipThrottle()` on the controller (the global auth throttler must not limit video playback redirects)
- `src/videos/videos.module.ts` — imports `TypeOrmModule.forFeature([Video])`, `ChannelsModule`, `StorageModule`; registered in `AppModule`

**Dependencies:** SI-03.2, SI-03.3

**Acceptance criteria:**

- Authenticated `POST /videos` with a 10GB declared size returns 201, `status: draft`, 11-char slug and 103 part URLs (100 MiB parts); a `videos` row exists
- Declared size above 10 GiB, non-`video/*` content type, or missing title → 400 `VALIDATION_ERROR`; no token → 401

**Tests:**

| File | Layer | Verifies |
|------|-------|----------|
| `src/videos/slug.util.spec.ts` | Unit | Length 11, URL-safe alphabet, uniqueness over many draws |
| `src/videos/videos.service.spec.ts` | Unit | Part planning, slug retry on unique violation, multipart abort compensation, channel not found |
| `src/videos/videos.service.integration-spec.ts` | Integration | Draft persisted with real DB + MinIO multipart opened |
| `test/videos.e2e-spec.ts` | E2E | `POST /videos` success, validation, auth |

---

### SI-03.6 — Upload Completion and Job Publication

**Description:** Finish the multipart upload, verify the real size, move the video to `processing` and publish the processing job. (`phase-03-videos/TD-01`, `TD-02`, `TD-07`)

**Technical actions:**

- `src/queue/bull-root.options.ts` — factory for `BullModule.forRootAsync` from `queueConfig`; `AppModule` imports `BullModule.forRootAsync(...)`
- `VideosModule` imports `BullModule.registerQueue({ name: VIDEO_PROCESSING_QUEUE })`
- `src/videos/dto/complete-upload.dto.ts` — `parts: { part_number, etag }[]`
- `VideosService.completeUpload(userId, slug, dto)` — owner + `draft` checks → `completeMultipartUpload` → `headObject` → if size > `VIDEO_MAX_FILE_SIZE_BYTES`: delete object, mark `failed`, throw `UploadSizeExceededException` → set `processing`, real `file_size`, clear `upload_id` → `queue.add('process-video', { videoId }, { jobId: videoId, attempts, backoff: exponential 5000, removeOnComplete, removeOnFail })`; enqueue failure → mark `failed` and rethrow
- `POST /videos/:slug/upload/complete` (authenticated, owner)

**Dependencies:** SI-03.5

**Acceptance criteria:**

- After uploading the parts to the presigned URLs, completion returns 200 with `status: processing` and a job with id = video id exists in the queue
- Non-owner → 404 `VIDEO_NOT_FOUND`; second completion → 409 `INVALID_VIDEO_STATUS`; bogus ETags → 400 `INVALID_UPLOAD_PARTS`

**Tests:**

| File | Layer | Verifies |
|------|-------|----------|
| `src/videos/videos.service.spec.ts` | Unit | Status guard, size-exceeded branch, enqueue options, enqueue-failure compensation |
| `src/videos/videos.service.integration-spec.ts` | Integration | Full complete with real MinIO + Redis queue (job present with `jobId = videoId`) |
| `test/videos.e2e-spec.ts` | E2E | Completion success and error cases |

---

### SI-03.7 — FFmpeg Service (Probe and Thumbnail)

**Description:** Wrap `ffprobe`/`ffmpeg` binaries. (`phase-03-videos/TD-04`)

**Technical actions:**

- `src/videos/processing/ffprobe.parser.ts` — `parseProbeOutput(json)` → `{ durationSeconds, metadata }`; throws `NotAVideoFileException` when no video stream
- `src/videos/processing/ffmpeg.service.ts` — `probe(input)` (`ffprobe -v error -print_format json -show_format -show_streams`); `extractFrame(input, atSeconds)` (`ffmpeg -ss … -frames:v 1 -vf scale=640:-2 -f image2 -c:v mjpeg pipe:1`) returning a JPEG `Buffer`; spawn with argument arrays and a timeout; `Invalid data found when processing input` → `NotAVideoFileException`

**Dependencies:** SI-03.1

**Acceptance criteria:**

- Probing a 2-second `lavfi` test video returns duration ≈ 2s, width/height, codecs; probing a text file throws `NotAVideoFileException`; extracted frame starts with the JPEG magic bytes

**Tests:**

| File | Layer | Verifies |
|------|-------|----------|
| `src/videos/processing/ffprobe.parser.spec.ts` | Unit | Duration/metadata mapping, audio-only and missing-stream inputs |
| `src/videos/processing/ffmpeg.service.integration-spec.ts` | Integration | Real binaries on a video generated at test time |

---

### SI-03.8 — Video Worker (Processor, Processing Service, Entrypoint)

**Description:** Consume the queue in a separate process, extract metadata, generate the thumbnail and finish the status lifecycle. (`phase-03-videos/TD-04`, `TD-07`)

**Technical actions:**

- `VideosService.findById`, `markReady(id, { durationSeconds, metadata, thumbnailKey })`, `markFailed(id, reason)`; `VideosModule` exports `VideosService`
- `src/videos/processing/video-processing.service.ts` — `process(videoId)`: not found → `VideoNotFoundException`; `ready` → no-op; not `processing` → `InvalidVideoStatusException`; presigned internal URL → `probe` → `extractFrame(min(1, duration/2))` → `putObject(videos/{id}/thumbnail.jpg)` → `markReady`
- `src/videos/processing/video.processor.ts` — `@Processor(VIDEO_PROCESSING_QUEUE)` `WorkerHost`; on `NotAVideoFileException` mark `failed` + throw `UnrecoverableError`; on `VideoNotFound`/`InvalidVideoStatus` throw `UnrecoverableError` (nothing to mark); other errors mark `failed` only on the last attempt and rethrow (BullMQ retries)
- `src/videos/processing/video-processing.module.ts` — imports `VideosModule`, `StorageModule`, `BullModule.registerQueue`; providers processor/service/ffmpeg
- `src/worker.module.ts` + `src/worker.ts` — `createApplicationContext(WorkerModule)` with Config, TypeORM, Bull root and `VideoProcessingModule`; graceful shutdown hooks
- Extract `configModuleOptions` (`src/config/config-module.options.ts`) and `typeOrmAsyncOptions` (`src/database/typeorm-options.factory.ts`) shared by `AppModule` and `WorkerModule`

**Dependencies:** SI-03.6, SI-03.7

**Acceptance criteria:**

- With a `processing` video in MinIO, `VideoProcessingService.process` leaves it `ready` with duration, metadata and a thumbnail object
- A non-video upload ends `failed` with `failure_reason` and is not retried
- `docker compose logs worker` shows the worker connected and processing jobs

**Tests:**

| File | Layer | Verifies |
|------|-------|----------|
| `src/videos/processing/video.processor.spec.ts` | Unit | Retry vs terminal failure branching, `UnrecoverableError` mapping |
| `src/videos/processing/video-processing.service.spec.ts` | Unit | Idempotency, thumbnail timestamp choice, status guards |
| `src/videos/processing/video-processing.service.integration-spec.ts` | Integration | Real DB + MinIO + FFmpeg: ready path and not-a-video path |
| `src/worker.module.integration-spec.ts` | Integration | `WorkerModule` boots as an application context (no HTTP server), connects to Postgres/Redis and runs the `video-processing` consumer |

---

### SI-03.9 — Video Read, Streaming, Download, and Thumbnail Endpoints

**Description:** Expose the unique URL and media delivery. (`phase-03-videos/TD-05`, `TD-06`, `TD-08`)

**Technical actions:**

- `VideosService.findVisibleBySlug(slug, viewerUserId?)` — `ready` visible to all, other statuses only to the owner, otherwise `VideoNotFoundException`
- `VideosService.getStreamUrl`, `getDownloadUrl` (require `ready` → `VideoNotReadyException`), `getThumbnailUrl` (`ThumbnailNotAvailableException`)
- Controller: `GET /videos/:slug` (200 `VideoResponseDto`), `GET /videos/:slug/stream`, `GET /videos/:slug/download`, `GET /videos/:slug/thumbnail` — all `@Public()` with optional auth, `302` with `Location` via `@Redirect()`

**Dependencies:** SI-03.4, SI-03.6

**Acceptance criteria:**

- Anonymous `GET /videos/:slug` of a draft → 404; owner → 200 with `status: draft`
- `GET /videos/:slug/stream` of a ready video → 302; following `Location` with `Range: bytes=0-1023` → `206` + `Content-Range`
- `GET /videos/:slug/download` → 302 to a URL whose response carries `Content-Disposition: attachment`

**Tests:**

| File | Layer | Verifies |
|------|-------|----------|
| `src/videos/videos.service.spec.ts` | Unit | Visibility rule, not-ready / thumbnail-missing errors |
| `test/videos.e2e-spec.ts` | E2E | Read/stream/download/thumbnail contracts and visibility |

---

### SI-03.10 — End-to-End Pipeline, OpenAPI Export, and AI Documentation

**Description:** Prove the whole pipeline over real infrastructure and update the docs. (all TDs)

**Technical actions:**

- `test/videos-pipeline.e2e-spec.ts` — generate a small MP4 with `ffmpeg -f lavfi`, `POST /videos`, `PUT` parts to the presigned URLs, complete, boot `WorkerModule` in-process, poll `GET /videos/:slug` until `ready`, assert duration/metadata/thumbnail, stream with Range (206) and download (attachment)
- Regenerate `nestjs-project/openapi.json` (`npm run openapi:export`)
- Update root `CLAUDE.md` (queue no longer TBD, videos section), `nestjs-project/CLAUDE.md` (new services, worker, env, commands), `README.md`, and `docs/diagrams/software-arch.mermaid` (queue = BullMQ/Redis)

**Dependencies:** SI-03.8, SI-03.9

**Acceptance criteria:**

- Pipeline e2e passes; full DoD (unit + integration + e2e, `tsc --noEmit`, lint, build) passes

**Tests:**

| File | Layer | Verifies |
|------|-------|----------|
| `test/videos-pipeline.e2e-spec.ts` | E2E | Upload → queue → worker → ready → stream 206 → download |

---

### SI-03.11 — Lint Baseline Correction (Definition of Done)

**Description:** Corrective SI (same pattern as SI-02.14): `npm run lint` already failed on the Phase 02 baseline (≈160 errors, almost all `no-unsafe-*`/`unbound-method`/`require-await` in test files where `supertest` bodies and jest mocks are `any` by nature). The DoD requires lint to pass.

**Technical actions:**

- `eslint.config.mjs` — override for `**/*.spec.ts`, `**/*.integration-spec.ts`, `**/*.e2e-spec.ts` turning off `no-unsafe-assignment`, `no-unsafe-member-access`, `no-unsafe-argument`, `no-unsafe-return`, `unbound-method`, `require-await` (type-safety rules remain enforced on `src/` production code)
- `src/channels/channels.service.ts` — type the Postgres driver error instead of `as any`
- `src/test/create-test-data-source.ts` — replace the `Function` type with a constructor type
- Remove two unused bindings in existing integration specs

**Dependencies:** None

**Acceptance criteria:**

- `docker compose exec nestjs-api npm run lint` exits 0 with 0 errors and 0 warnings
- Full test suite still green

**Tests:** no new tests (lint/type-level change)

---

## Technical Specifications

### Data Model

#### Video (`videos`)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | uuid | PK | Generated by the API (`randomUUID()`) before the insert so the storage key can embed it |
| channel_id | uuid | FK → channels.id `ON DELETE CASCADE`, not null | Owner channel |
| title | varchar(100) | not null | Initial title sent at upload start (editable in Phase 04) |
| slug | varchar(11) | unique, not null | Public unique URL id — base64url of 8 random bytes |
| status | enum `videos_status_enum` (`draft`, `processing`, `ready`, `failed`) | not null, default `draft` | Processing lifecycle |
| original_file_name | varchar(255) | not null | Used as the download file name |
| mime_type | varchar(100) | not null | Declared `video/*` type; served as stream `Content-Type` |
| file_size | bigint | not null | Declared size at creation; replaced by the real size after completion (transformer → `number`) |
| video_key | varchar(512) | not null | `videos/{id}/source` |
| upload_id | varchar(1024) | nullable | S3 multipart upload id while `draft`; cleared after completion |
| thumbnail_key | varchar(512) | nullable | `videos/{id}/thumbnail.jpg` once processed |
| duration_seconds | double precision | nullable | From ffprobe `format.duration` |
| metadata | jsonb | nullable | `{ format_name, bit_rate, width, height, video_codec, audio_codec, frame_rate }` |
| failure_reason | text | nullable | Set when `failed` |
| processed_at | timestamptz | nullable | Set when `ready` |
| created_at | timestamp | not null, auto | `@CreateDateColumn` |
| updated_at | timestamp | not null, auto | `@UpdateDateColumn` |

**Relations:** Video → Channel (many-to-one, owning side `channel_id`); Channel → Video (one-to-many inverse `videos`).
**Indexes:** `(slug)` unique; `(channel_id)`.

#### Object storage layout (bucket `S3_BUCKET`, private)

| Key | Content | Written by |
|-----|---------|-----------|
| `videos/{videoId}/source` | Original upload (multipart) | Client via presigned part URLs |
| `videos/{videoId}/thumbnail.jpg` | 640px-wide JPEG frame | Worker |

---

### API Contracts

All error bodies follow the shared envelope `{ statusCode, error, message }` (`phase-02-auth/TD-07`).

#### POST /videos (SI-03.5)

**Request headers:** `Authorization: Bearer <access_token>`, `Content-Type: application/json`

**Request body:**
- title: string, required — trimmed, 1–100 chars
- file_name: string, required — 1–255 chars
- file_size: integer, required — 1 … 10,737,418,240 (10 GiB)
- content_type: string, required — matches `^video\/[a-z0-9.+-]+$` (case-insensitive)

**Response 201:**
- video: `VideoResponse` (status `draft`)
- upload.upload_id: string
- upload.part_size: integer (bytes)
- upload.part_count: integer
- upload.expires_at: string (ISO-8601)
- upload.parts: `{ part_number: integer, url: string }[]` — client `PUT`s bytes `[(n-1)·part_size, n·part_size)` to each URL and keeps the returned `ETag` header

**Error responses:**
- 400 VALIDATION_ERROR — invalid body
- 401 — missing/invalid access token
- 404 CHANNEL_NOT_FOUND — authenticated user has no channel

#### POST /videos/:slug/upload/complete (SI-03.6)

**Request headers:** `Authorization: Bearer <access_token>`, `Content-Type: application/json`

**Request body:**
- parts: array (1–10,000) of `{ part_number: integer 1–10,000, etag: string non-empty }`

**Response 200:** `VideoResponse` (status `processing`)

**Error responses:**
- 400 VALIDATION_ERROR — invalid body or malformed slug
- 400 INVALID_UPLOAD_PARTS — storage rejected the part list (missing/unknown part, wrong ETag, part too small)
- 401 — missing/invalid access token
- 404 VIDEO_NOT_FOUND — unknown slug or caller is not the owner
- 409 INVALID_VIDEO_STATUS — video is not `draft`
- 422 UPLOAD_SIZE_EXCEEDED — stored object larger than 10 GiB (object deleted, video `failed`)

#### GET /videos/:slug (SI-03.9)

**Request headers:** optional `Authorization: Bearer <access_token>`

**Response 200:** `VideoResponse`:
- id (uuid), slug, title, status, channel_id, original_file_name, mime_type, file_size (integer), duration_seconds (number | null), metadata (object | null), failure_reason (string | null), processed_at (ISO | null), created_at, updated_at

**Error responses:**
- 400 VALIDATION_ERROR — malformed slug
- 404 VIDEO_NOT_FOUND — unknown slug, or video not `ready` and caller is not the owner

#### GET /videos/:slug/stream (SI-03.9)

**Response 302:** `Location` = presigned GET (public endpoint, `Content-Type` = video MIME, expires in `STREAM_URL_EXPIRATION_SECONDS`). The storage answers `Range` requests with `206 Partial Content` + `Content-Range` + `Accept-Ranges: bytes`.

**Error responses:** 400 VALIDATION_ERROR; 404 VIDEO_NOT_FOUND; 409 VIDEO_NOT_READY (owner, non-ready video)

#### GET /videos/:slug/download (SI-03.9)

**Response 302:** `Location` = presigned GET with `response-content-disposition=attachment; filename="<original_file_name>"`.

**Error responses:** 400 VALIDATION_ERROR; 404 VIDEO_NOT_FOUND; 409 VIDEO_NOT_READY

#### GET /videos/:slug/thumbnail (SI-03.9)

**Response 302:** `Location` = presigned GET of `thumbnail.jpg`.

**Error responses:** 400 VALIDATION_ERROR; 404 VIDEO_NOT_FOUND; 404 THUMBNAIL_NOT_AVAILABLE

#### Validation Rules

| Field | Rule | Error message (class-validator) |
|-------|------|---------------|
| title | string, 1–100 after trim | title must be shorter than or equal to 100 characters |
| file_name | string, 1–255 | file_name must be shorter than or equal to 255 characters |
| file_size | integer, ≥ 1, ≤ 10737418240 | file_size must not be greater than 10737418240 |
| content_type | `^video\/[a-z0-9.+-]+$`i | content_type must be a video MIME type |
| :slug | `^[A-Za-z0-9_-]{11}$` | slug must be a valid video slug |
| parts[].part_number | integer 1–10000 | part_number must not be greater than 10000 |
| parts[].etag | non-empty string | etag should not be empty |

---

### Authorization Matrix

| Endpoint | Public | Authenticated | Owner only | Notes |
|----------|--------|---------------|------------|-------|
| POST /videos | | ✓ | | Video created in the caller's channel |
| POST /videos/:slug/upload/complete | | ✓ | ✓ | Non-owner gets 404 (draft not disclosed) |
| GET /videos/:slug | ✓ | | | `ready`: everyone; other statuses: owner only (optional auth, TD-08) |
| GET /videos/:slug/stream | ✓ | | | Same visibility; requires `ready` |
| GET /videos/:slug/download | ✓ | | | Same visibility; requires `ready` |
| GET /videos/:slug/thumbnail | ✓ | | | Same visibility; requires thumbnail |

`VideosController` carries `@SkipThrottle()`: the global `ThrottlerGuard` registered by `AuthModule` (10 req/min) would otherwise throttle every seek of a player hitting `/stream`.

---

### Error Catalog

| Code | HTTP | Message | Trigger |
|------|------|---------|---------|
| CHANNEL_NOT_FOUND | 404 | Channel not found for the current user | `POST /videos` when the user has no channel |
| VIDEO_NOT_FOUND | 404 | Video not found | Unknown slug, not visible to caller, or completion by non-owner |
| INVALID_VIDEO_STATUS | 409 | Video is not in a valid status for this operation | Completion when status ≠ `draft` |
| INVALID_UPLOAD_PARTS | 400 | Uploaded parts are invalid or incomplete | Storage rejects `CompleteMultipartUpload` |
| UPLOAD_SIZE_EXCEEDED | 422 | Uploaded file exceeds the 10 GB limit | Real object size > 10 GiB |
| VIDEO_NOT_READY | 409 | Video is not ready yet | Stream/download of non-ready video by its owner |
| THUMBNAIL_NOT_AVAILABLE | 404 | Thumbnail not available | Thumbnail requested before processing |
| NOT_A_VIDEO_FILE | — (worker only) | File is not a valid video | ffprobe finds no video stream / invalid data → video `failed` |
| VALIDATION_ERROR | 400 | (array of field errors) | DTO / param validation |

---

### Events/Messages

#### Queue `video-processing` — job `process-video`

| Item | Value |
|------|-------|
| Transport | BullMQ on Redis (`REDIS_HOST:REDIS_PORT`) |
| Producer | `VideosService.completeUpload` (API process) |
| Consumer | `VideoProcessor` (worker process, `src/worker.ts`) |
| Payload | `{ videoId: string (uuid) }` |
| Job id | `videoId` — dedup: completing twice cannot enqueue two active jobs |
| Attempts | `VIDEO_PROCESSING_ATTEMPTS` (default 3) |
| Backoff | exponential, 5000 ms base |
| Retention | `removeOnComplete: 1000`, `removeOnFail: 5000` |

**Consumer outcomes:**

| Situation | DB effect | Job outcome |
|-----------|-----------|-------------|
| Success | `status = ready`, `duration_seconds`, `metadata`, `thumbnail_key`, `processed_at` | completed |
| Video already `ready` | none (idempotent) | completed |
| Not a video (`NotAVideoFileException`) | `status = failed`, `failure_reason` | failed (`UnrecoverableError`, no retry) |
| Video missing / not `processing` | none | failed (`UnrecoverableError`) |
| Transient error, attempts left | none | retried with backoff |
| Transient error, last attempt | `status = failed`, `failure_reason` | failed |

**Status lifecycle:** `draft` (POST /videos) → `processing` (upload completed + job enqueued) → `ready` | `failed`. Also `draft → failed` when the real size exceeds 10 GiB or enqueueing fails.

---

## Dependency Map

```
SI-03.1 (no deps)
├── SI-03.2
├── SI-03.3
└── SI-03.7

SI-03.4 (no deps)

SI-03.2 + SI-03.3
└── SI-03.5
    └── SI-03.6
        ├── SI-03.8  (also needs SI-03.7)
        └── SI-03.9  (also needs SI-03.4)

SI-03.8 + SI-03.9
└── SI-03.10

SI-03.11 (no deps — corrective, lint baseline)
```

Linearized implementation order: SI-03.1 → SI-03.2, SI-03.3, SI-03.4, SI-03.7 (parallel) → SI-03.5 → SI-03.6 → SI-03.8, SI-03.9 (parallel) → SI-03.10 → SI-03.11

## Deliverables

- [ ] MinIO (+ bucket init), Redis and the video worker running in `docker compose` next to API, DB and Mailpit
- [ ] `videos` table (migration) linked to `channels`, with status, storage keys, duration, metadata and unique slug
- [ ] `POST /videos` pre-registers a `draft` and returns presigned multipart URLs — no video byte passes through the API (up to 10 GB)
- [ ] `POST /videos/:slug/upload/complete` verifies the real size, sets `processing` and publishes the `process-video` job
- [ ] Worker extracts duration/metadata with ffprobe and generates a JPEG thumbnail with ffmpeg; status ends `ready` or `failed` (with reason)
- [ ] Unique 11-char slug per video, guaranteed by a unique index with retry
- [ ] `GET /videos/:slug/stream` redirects to storage answering Range with `206 Partial Content`; `GET /videos/:slug/download` serves the original as attachment; `GET /videos/:slug/thumbnail`
- [ ] Optional authentication on public routes (owner sees non-ready videos)
- [ ] Lint baseline fixed (`npm run lint` exits 0)
- [ ] OpenAPI (`openapi.json`) regenerated; `CLAUDE.md` files updated with the videos section
- [ ] All tests pass (`docker compose exec nestjs-api npm test -- --runInBand`)
- [ ] E2E tests pass (`docker compose exec nestjs-api npm run test:e2e`)
- [ ] Type check passes (`docker compose exec nestjs-api npx tsc --noEmit`)
- [ ] Lint passes (`docker compose exec nestjs-api npm run lint`)
- [ ] Project builds (`docker compose exec nestjs-api npm run build`)
