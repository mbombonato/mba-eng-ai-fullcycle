# CLAUDE.md

## Environment Startup Verification

**Default behavior:** starting the environment means starting **only infrastructure services** (database, mail, etc.) — **never** start the NestJS application server unless the user explicitly asks to run/serve the project (e.g., "rode o projeto", "suba o servidor", "run the app").

After starting infrastructure, always confirm the containers are up before proceeding:

```bash
docker compose ps   # all services must show status "running"
```

Then verify each infrastructure service is actually ready to accept connections — not just running:

- **PostgreSQL:** `docker compose exec db pg_isready -U streamtube` — expect `accepting connections`
- **Redis:** `docker compose exec redis redis-cli ping` — expect `PONG`
- **MinIO:** `docker compose ps minio` shows `healthy`, and `docker compose ps -a minio-init` shows `Exited (0)` (bucket created)

Only start the NestJS dev server (`npm run start:dev`) when the user **explicitly** asks to run the application — never as part of "start the environment".

## Development Environment

This project runs inside Docker. Always use the container for development:

```bash
# Start containers
docker compose up -d

# Install dependencies (first time only)
docker compose exec nestjs-api npm install

# Run the dev server (watch mode)
docker compose exec nestjs-api npm run start:dev
```

Services:
- `nestjs-api` — NestJS API, port `3000`
- `db` — PostgreSQL 17, port `5432`, database `streamtube`, user/password `streamtube`
- `mailpit` — SMTP `1025`, web UI `8025`
- `minio` — S3-compatible object storage (`pgsty/minio`, the official `minio/minio` image is no longer published), API `9000`, console `9001`, credentials = `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY`
- `minio-init` — one-shot container that creates the private bucket `S3_BUCKET` (`mc mb --ignore-existing`) and exits `0`
- `redis` — Redis 7.4 (AOF on), port `6379`, backend of the BullMQ queue
- `worker` — video worker: same image/bind mount as `nestjs-api`, runs `npm run start:worker` (`src/worker.ts`), `restart: unless-stopped`. It shares `node_modules` with the API, so it keeps restarting until `npm install` has been run once

All verification and teardown commands run on the **host machine**:

```bash
# Verify NestJS is running (expect 200 + "Hello World!")
curl http://localhost:3000

# Verify PostgreSQL is ready (runs inside the db container)
docker compose exec db pg_isready -U streamtube

# Check container logs
docker compose logs nestjs-api
docker compose logs db
docker compose logs worker   # expect "Video worker started — consuming \"video-processing\""

# Tear down the entire environment
docker compose down
```

## Commands

**Strict rule:** every `npm`, `npx`, `node`, `tsc`, and test command runs **inside the container**, never on the host. Running on the host causes env-var divergence (`DB_HOST` resolves to `localhost` instead of the Compose service), uses a different Node version, and produces results that do not reflect what runs in CI/prod.

### Container-only commands (always prefix with `docker compose exec nestjs-api`)

```bash
npm run start:dev                        # Dev server with hot-reload
npm run build                            # Compile to dist/
npm run start:prod                       # Run compiled build
npm run start:worker                     # Video worker (already started by the `worker` service)
npm run start:worker:prod                # Compiled video worker (dist/worker.js)
npm run migration:run                    # Apply migrations (creates `videos` in Phase 03)
npm run openapi:export                   # Regenerate openapi.json

npm test                                 # Unit + integration tests (serial, maxWorkers: 1)
npm run test:watch                       # Unit tests in watch mode
npm run test:cov                         # Coverage report
npm run test:e2e                         # End-to-end tests (serial, maxWorkers: 1)

npx tsc --noEmit                         # Type-check (required before declaring a task done)
npm run lint                             # ESLint with auto-fix
npm run format                           # Prettier formatting
```

### Host-only commands (Docker / connectivity probes)

```bash
docker compose ps
docker compose logs nestjs-api
docker compose exec db pg_isready -U streamtube
curl http://localhost:3000
```

### Test execution

Integration and e2e suites share a single test database, bucket and Redis. They **must** run serially — both Jest configs set `maxWorkers: 1` (equivalent to `--runInBand`), so the plain commands are already safe:

```bash
docker compose exec nestjs-api npm test
docker compose exec nestjs-api npm run test:e2e
```

Parallel execution causes FK violations, deadlocks, and cross-suite contamination because suites truncate or seed shared tables concurrently.

Video tests use the real infrastructure: MinIO (multipart upload, presigned URLs), Redis (BullMQ jobs) and the `ffmpeg`/`ffprobe` binaries of the container (test videos are generated at runtime with `ffmpeg -f lavfi`, see `src/test/media.ts`). Presigned URLs embed the signed host, so tests call `signPresignedUrlsWithInternalEndpoint()` (`src/test/storage.ts`) to sign with `http://minio:9000` instead of the browser-facing `S3_PUBLIC_ENDPOINT`. The `worker` container may also consume jobs enqueued by tests; this is expected (tests that need a result boot `WorkerModule` in-process and poll the video status).

During active development, run only the tests related to the file being changed (`npm test -- path/to/file.spec.ts`). Before declaring a task done, run the full suite — see the global `CLAUDE.md` → "Definition of Done (Technical)".

## Long-running Processes

Commands that never exit (dev server, watch modes) must be run in background in the Bash tool — otherwise the agent blocks indefinitely waiting for the process to return.

This applies to: `start:dev`, `start:prod`, `test:watch`, and any other persistent process.

## Test Type Selection

Choose the suffix by what the test really does, not by where the code under test lives. The suffix is a contract that drives Jest config (`testRegex`, parallelism), CI steps, and reader expectations.

| Suffix                  | Purpose                                                              | DB / external I/O | Location                     |
|-------------------------|----------------------------------------------------------------------|-------------------|------------------------------|
| `*.spec.ts`             | **Unit** — pure logic, all collaborators mocked                      | Forbidden         | Next to the source file      |
| `*.integration-spec.ts` | **Integration** — exercises real DB, real repositories, real modules | Required          | Next to the source file      |
| `*.e2e-spec.ts`         | **End-to-end** — full HTTP cycle via `supertest`                     | Required          | `nestjs-project/test/`       |

A test that constructs a `TypeOrmModule.forRoot`, opens a connection, or hits the `db` service **must** be `*.integration-spec.ts`, never `*.spec.ts`. A test that boots the full Nest application and makes HTTP calls **must** be `*.e2e-spec.ts`.

Conventions for **how to write** each kind of test (mocking patterns, AAA structure, override strategies for global guards, etc.) live in `.claude/rules/nestjs-testing.md` and load when you edit a test file.

## Jest Configuration

These settings are required in `package.json` (jest config) and `test/jest-e2e.json` for the project's tests to work correctly:

- `setupFiles: ["dotenv/config"]` — without this, `.env` is not loaded inside the Jest process. `DB_HOST`, `JWT_SECRET`, etc. fall back to undefined or to the host's `localhost`, breaking container-to-container DNS.
- `testRegex: '.*\\.(spec|integration-spec)\\.ts$'` — covers both unit (`*.spec.ts`) and integration (`*.integration-spec.ts`) suffixes.
- `maxWorkers: 1` — serial execution (shared DB, bucket and queue; see "Test execution").

Do not add new test-file suffixes; if a new test type is needed, update the regex deliberately.

## Environment File Conventions

`.env` is parsed by both Docker Compose and `dotenv` — values containing shell-special characters (`<`, `>`, `|`, `&`, spaces) **must be quoted** or rewritten:

```dotenv
# Wrong — the unquoted angle brackets are shell redirection syntax and break parsing
MAIL_FROM=StreamTube <noreply@streamtube.local>

# Right — quote the value
MAIL_FROM="StreamTube <noreply@streamtube.local>"
```

Whenever possible, prefer storing only the bare address in `.env` and composing display names in code (e.g., in `mail.config.ts`) so the file stays shell-safe.

## Build Assets

`tsc` (and therefore `nest build`) only emits compiled `.ts` files to `dist/`. Any non-TypeScript runtime asset — Handlebars templates (`.hbs`), JSON fixtures, static config files, etc. — must be declared in `nest-cli.json` under `compilerOptions.assets` (with `watchAssets: true` for dev). Without that, the file exists in `src/` but is missing in `dist/` and runtime fails only after build.

## Architecture

NestJS with standard module structure. Source lives in `src/`, compiled output in `dist/`.

- Each domain feature gets its own module (e.g., `UsersModule`, `VideosModule`) registered in `AppModule`
- Controllers handle HTTP routing; Services hold business logic; both are scoped to their module

## Videos, Storage, Queue and Worker (Phase 03)

Plan: `docs/phases/phase-03-videos/phase-03-videos.md`. Decisions: `docs/decisions/technical-decisions-phase-03-videos.md` (TD-01…TD-08).

### Modules

- `src/storage/` — `StorageModule` / `StorageService`: the **only** place that talks to S3/MinIO. Two `S3Client`s (`s3-client.factory.ts`, tokens in `storage.constants.ts`): `S3_CLIENT` uses `S3_ENDPOINT` (server-to-server, `http://minio:9000`) and `S3_PRESIGN_CLIENT` signs client-facing URLs with `S3_PUBLIC_ENDPOINT`. Operations: multipart (`createMultipartUpload`, `presignUploadParts`, `completeMultipartUpload` — S3 part errors become `InvalidUploadPartsException`, `abortMultipartUpload`), `headObject`, `putObject`, `deleteObject`, `presignDownloadUrl` (public, optional `Content-Type`/attachment file name) and `presignInternalDownloadUrl` (internal endpoint, used by the worker).
- `src/videos/` — `VideosModule` (registered in `AppModule`): `Video` entity (`entities/video.entity.ts`, many-to-one `Channel`, `ON DELETE CASCADE`), `VideosService`, `VideosController`, DTOs in `dto/`, constants (`VideoStatus`, 10 GiB limit, slug, queue/job names, storage keys) in `videos.constants.ts`, slug generator in `slug.util.ts`. Exports `VideosService` for the worker.
- `src/videos/processing/` — worker side, `VideoProcessingModule`: `VideoProcessor` (`@Processor('video-processing')`, `WorkerHost`), `VideoProcessingService` (probe → thumbnail → `markReady`), `FfmpegService` (`ffprobe`/`ffmpeg` via `child_process.spawn` with argument arrays and a timeout) and `ffprobe.parser.ts`.
- `src/queue/bull-root.options.ts` — shared `BullModule.forRootAsync` options (Redis from the `queue` config namespace), used by `AppModule` and `WorkerModule`.
- `src/worker.ts` + `src/worker.module.ts` — the worker process: `NestFactory.createApplicationContext(WorkerModule)` (no HTTP server). `WorkerModule` reuses `configModuleOptions` (`src/config/config-module.options.ts`) and `typeOrmAsyncOptions` (`src/database/typeorm-options.factory.ts`) shared with `AppModule`.
- `src/database/migrations/1794254173397-CreateVideos.ts` — `videos` table + `videos_status_enum`.

### Flow

1. `POST /videos` (JWT) — validates `title`, `file_name`, `file_size` (≤ 10 GiB) and `content_type` (`video/*`); opens an S3 multipart upload at `videos/{id}/source`, inserts the video as **`draft`** with a unique 11-char base64url slug (unique index + retry, max 5) and returns one presigned `PUT` URL per part (`UPLOAD_PART_SIZE_MB`, default 100 MiB). **No video byte goes through the API** — the client uploads straight to the storage.
2. `POST /videos/:slug/upload/complete` (JWT, owner) — completes the multipart upload, checks the real size with `headObject` (> 10 GiB → object deleted, video `failed`, 422), sets **`processing`** and enqueues job `process-video` `{ videoId }` on queue `video-processing` (`jobId = videoId`, `VIDEO_PROCESSING_ATTEMPTS` attempts, exponential backoff 5 s). Enqueue failure → video `failed`.
3. Worker — reads the source via a presigned internal URL, `ffprobe` → duration + metadata (`format_name`, `bit_rate`, `width`, `height`, `video_codec`, `audio_codec`, `frame_rate`), `ffmpeg` extracts one 640px JPEG frame → `videos/{id}/thumbnail.jpg`, then **`ready`**. Not a video → `failed` with `failure_reason`, no retry (`UnrecoverableError`); transient errors are retried and mark `failed` only on the last attempt; an already `ready` video is a no-op.
4. Delivery — `GET /videos/:slug`, `/stream`, `/download`, `/thumbnail` are `@Public()`; media routes answer `302` to a short-lived presigned GET (`STREAM_URL_EXPIRATION_SECONDS`). The storage serves `Range` requests with `206 Partial Content` (streaming); `/download` signs `Content-Disposition: attachment` with the original file name.

Status lifecycle: `draft → processing → ready | failed` (also `draft → failed`). Visibility: `ready` videos are visible to everyone; other statuses only to the owner (404 otherwise).

### Endpoints

| Method & Route | Auth | Success | Errors |
|----------------|------|---------|--------|
| `POST /videos` | JWT | 201 `{ video, upload }` | 400 `VALIDATION_ERROR`, 401, 404 `CHANNEL_NOT_FOUND` |
| `POST /videos/:slug/upload/complete` | JWT, owner | 200 video (`processing`) | 400 `VALIDATION_ERROR` / `INVALID_UPLOAD_PARTS`, 401, 404 `VIDEO_NOT_FOUND`, 409 `INVALID_VIDEO_STATUS`, 422 `UPLOAD_SIZE_EXCEEDED` |
| `GET /videos/:slug` | public (optional JWT) | 200 video | 400, 404 `VIDEO_NOT_FOUND` |
| `GET /videos/:slug/stream` | public (optional JWT) | 302 → storage (Range/206) | 400, 404, 409 `VIDEO_NOT_READY` |
| `GET /videos/:slug/download` | public (optional JWT) | 302 → storage (attachment) | 400, 404, 409 `VIDEO_NOT_READY` |
| `GET /videos/:slug/thumbnail` | public (optional JWT) | 302 → storage (JPEG) | 400, 404 `VIDEO_NOT_FOUND` / `THUMBNAIL_NOT_AVAILABLE` |

`VideosController` uses `@SkipThrottle()` so the global auth throttler (10 req/min) does not limit player seeks.

### Optional authentication on public routes

`JwtAuthGuard` (`src/auth/guards/jwt-auth.guard.ts`): on `@Public()` routes a valid `Bearer` token populates `request.user`; an invalid or missing token is ignored and the request proceeds anonymously. Protected routes are unchanged. This is how public video routes recognize the owner.

### Environment variables (validated in `src/config/env.validation.ts`)

| Variable | Default | Notes |
|----------|---------|-------|
| `S3_ENDPOINT` | `http://minio:9000` | Server-to-server endpoint (Compose service name) |
| `S3_PUBLIC_ENDPOINT` | `http://localhost:9000` | Host used to sign URLs handed to clients (browser) |
| `S3_REGION` | `us-east-1` | |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | — (required) | Also MinIO root credentials in Compose |
| `S3_BUCKET` | `streamtube` | Private bucket created by `minio-init` |
| `S3_FORCE_PATH_STYLE` | `true` | Required by MinIO |
| `REDIS_HOST` / `REDIS_PORT` | `redis` / `6379` | BullMQ connection |
| `UPLOAD_PART_SIZE_MB` | `100` | 5–5120 |
| `UPLOAD_URL_EXPIRATION_SECONDS` | `86400` | Presigned part URL lifetime (max 604800) |
| `STREAM_URL_EXPIRATION_SECONDS` | `3600` | Stream/download/thumbnail URL lifetime |
| `VIDEO_PROCESSING_ATTEMPTS` | `3` | BullMQ attempts per job |

## Code Conventions

- **TypeScript:** `nodenext` module resolution, `ES2023` target, `strictNullChecks` on, `noImplicitAny` off
- **Decorators:** `emitDecoratorMetadata` + `experimentalDecorators` enabled — required for NestJS DI
- **Prettier:** single quotes, trailing commas everywhere
- **ESLint:** `no-explicit-any` allowed; `no-floating-promises` and `no-unsafe-argument` are warnings

## REST Conventions

This is a RESTful API. All endpoints must follow standard REST conventions — correct HTTP methods, proper status codes, plural resource nouns, and consistent URL structure. Details are enforced via rules on controller files.
