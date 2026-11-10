---
scope_type: phase
related_phases: [3]
status: decided
date: 2026-11-09
scope_description: "Backend foundation for video upload and processing: job queue technology, 10GB upload strategy, object-storage layout, video worker runtime and FFmpeg usage, unique video URL, streaming/download delivery, and the video status lifecycle with failure handling."
---

# Technical Decisions — Phase 03: Upload e Processamento de Vídeos

_Subprojects in scope:_

- `nestjs-project/` — receives the `videos` module (API), the `storage` module (S3/MinIO), the queue producer, the video worker entrypoint (FFmpeg) and the new Compose services (MinIO, Redis, worker).
- `next-frontend/` — no open decision in this document. The challenge statement for Phase 03 declares the video UI out of scope ("a interface de vídeo não faz parte do escopo desta fase"); the upload/player screens are deferred to the phases that own them (Fase 04/05).

**Fixed constraint (not reopened):** object storage is **S3-compatible** — **MinIO** locally in Docker, AWS S3 in production (`docs/diagrams/software-arch.mermaid`: "Object Storage — S3 or MinIO"). This document decides *how* storage is used, not *which* storage.

**Inherited constraints:** `phase-01-configuracao-base/TD-01..TD-04` (namespaced `registerAs` config + Joi validation), `phase-02-auth/TD-02` (global `JwtAuthGuard`, `@Public()` opt-out), `phase-02-auth/TD-06` (class-validator DTOs), `phase-02-auth/TD-07` (domain exception filter, `{ statusCode, error, message }` envelope). Every service runs in Docker and is addressed by its Compose service name (`CLAUDE.md` → Docker Networking).

**Library documentation note:** the context7 MCP server is not configured in this workspace's `.mcp.json` (only `postgres`). Library APIs were checked against the official documentation/changelogs (docs.bullmq.io, BullMQ GitHub changelog, docs.nestjs.com/techniques/queues, AWS SDK for JavaScript v3 docs, MinIO docs, FFmpeg docs) and against the registry metadata (`npm view`) from inside the `nestjs-api` container. See `docs/phases/phase-03-videos/library-refs.md`.

---

## TD-01: Message Queue Technology for Video Processing Jobs

**Scope:** Backend

**Capability:** Serviço de processamento em segundo plano (filas)

**Context:** The architecture diagram leaves the queue as "TBD". The API must publish a processing job when an upload finishes and a separate worker must consume it, with retries and a terminal failure state. This is the main stack decision of the phase; it adds one new infrastructure container (or none, for the Postgres option).

**Options:**

### Option A: BullMQ + Redis (`@nestjs/bullmq`)
- Redis-backed job queue for Node.js. The API adds jobs with `Queue.add()`; a `Worker` (wrapped by `@Processor` / `WorkerHost` in `@nestjs/bullmq`) consumes them. Built-in retries (`attempts`), exponential `backoff`, job ids for deduplication, concurrency control, `UnrecoverableError` to skip retries, and completed/failed retention policies.
- **Pros:** Official NestJS integration (docs.nestjs.com/techniques/queues) — `BullModule.forRootAsync` + `registerQueue` + `@InjectQueue`. Job semantics (retry/backoff/dedup by `jobId`) cover the needs of video processing with little custom code. Redis is a single lightweight container (`redis:7-alpine`). Producer and consumer can live in different processes/containers sharing the same codebase.
- **Cons:** Adds Redis as a new stateful service. At-least-once delivery — the worker must be idempotent. Redis persistence must be configured if jobs must survive a Redis restart (AOF).

### Option B: RabbitMQ (`@nestjs/microservices` RMQ transport or `amqplib`)
- AMQP broker with exchanges/queues, acks and dead-letter exchanges. NestJS offers it as a microservice transport (`@EventPattern`) or via raw `amqplib`.
- **Pros:** Mature broker, strong delivery guarantees, DLX for failed messages, language-agnostic (a non-Node worker could consume it).
- **Cons:** Heavier container and operational surface (management UI, vhosts, users). Retry with backoff requires manual DLX/TTL topology. The NestJS microservice transport is message-oriented (no job state, no built-in attempts/backoff/progress). More code for the same result.

### Option C: Postgres-backed queue (pg-boss)
- Job queue implemented on PostgreSQL tables with `SKIP LOCKED`. Reuses the existing `db` service.
- **Pros:** No new infrastructure. Jobs can be enqueued in the same DB transaction as the video update (transactional outbox for free).
- **Cons:** No official NestJS module (community wrappers only). Polling load on the main database, which also serves the API. The architecture diagram models the queue as its own container — this option would collapse it into the database, contradicting the target design.

**Recommendation:** **Option A (BullMQ + Redis)** — first-class NestJS integration and native retry/backoff/dedup semantics keep the worker small; Redis is a single extra container and matches the diagram's separate "Message Queue" container. Version pin: `bullmq@~5.81.5` (the mature 5.x line — 6.0.0, released 2026-07-30, removed Redis internals from the public API and turned `ioredis` into an optional peer; `@nestjs/bullmq@11.0.5` supports both, but the 5.x line is the one documented by the NestJS recipe) with `@nestjs/bullmq@^11.0.5` (NestJS 11 peer).

**Decision:** A (BullMQ + Redis)

**Libraries:** `bullmq@~5.81.5`, `@nestjs/bullmq@^11.0.5`

---

## TD-02: 10GB Upload Strategy

**Scope:** Backend

**Capability:** Transversal — covers: "Upload de vídeos com suporte a arquivos de até 10GB sem impacto na performance", "Pré-cadastro automático do vídeo como rascunho ao iniciar o upload"

**Context:** A 10GB body cannot transit the API without tying up a Node process, memory/disk buffers and a long-lived HTTP connection for minutes or hours. A single S3 `PUT` is limited to 5GB, so a 10GB object *requires* multipart upload. The strategy also defines when the draft is created.

**Options:**

### Option A: Multipart upload through the API (Multer / streaming proxy)
- Client sends `multipart/form-data` to the API; the API streams it to S3 (e.g., `@aws-sdk/lib-storage` `Upload`).
- **Pros:** Simple client; API controls the bytes.
- **Cons:** Every byte passes through the API — exactly what the phase forbids ("sem travar o sistema"). Long requests are fragile (timeouts, proxies), no resume, API bandwidth/CPU scales with uploads.

### Option B: Direct-to-storage S3 multipart upload with presigned part URLs
- `POST /videos` validates metadata (title, declared size ≤ 10GB, `video/*` MIME), calls `CreateMultipartUpload`, pre-registers the video as **draft**, and returns one presigned `UploadPart` URL per part (fixed part size). The client `PUT`s the parts straight to S3/MinIO (in parallel, retrying individual parts) and then calls `POST /videos/:slug/upload/complete` with the `{ part_number, etag }` list; the API calls `CompleteMultipartUpload`, verifies the real object size with `HeadObject`, and enqueues processing.
- **Pros:** Zero video bytes through the API — the API only signs URLs (offline HMAC, no I/O per part). Supports up to 10,000 parts / 5TB, parallel and per-part retry. Standard S3 protocol, identical on MinIO and AWS. Draft creation naturally happens at upload start.
- **Cons:** Client must split the file and track ETags (browser needs CORS with `ETag` exposed on the bucket). Presigned URLs expire — a very slow upload must finish within the expiry window. Orphan multipart uploads (abandoned drafts) need a lifecycle rule (`AbortIncompleteMultipartUpload`) in production.

### Option C: tus resumable upload server (tusd / @tus/server)
- Separate tus server receives chunks with offset-based resume and writes to S3.
- **Pros:** Best resume UX, standard protocol with mature clients (Uppy).
- **Cons:** Another server in the data path (bytes still pass through a service we run), new container plus hook integration to create the draft/enqueue. Overkill when S3 multipart already offers part-level retry.

**Recommendation:** **Option B (direct S3 multipart with presigned part URLs)** — the only option where the API never touches the video bytes, using the storage's native protocol. Parameters: part size `UPLOAD_PART_SIZE_MB` (default 100 MiB → a 10GB file is 103 parts, well under the 10,000-part limit; S3 minimum is 5 MiB), max size fixed by the business rule as the constant `VIDEO_MAX_FILE_SIZE_BYTES` (10 GiB = 10,737,418,240 bytes — a product requirement, not an environment knob), presigned URL expiry `UPLOAD_URL_EXPIRATION_SECONDS` (default 24h). The declared size is validated in the DTO and the **actual** size is re-checked with `HeadObject` after completion (an over-limit object is deleted and the video marked `failed`).

**Decision:** B (Direct-to-storage S3 multipart with presigned part URLs)

**Libraries:** `@aws-sdk/client-s3@~3.1156.0`, `@aws-sdk/s3-request-presigner@~3.1156.0`

---

## TD-03: Object Storage Layout and S3 Client Configuration

**Scope:** Backend

**Capability:** Serviço de armazenamento de arquivos (vídeos e thumbnails)

**Context:** Storage is fixed as S3/MinIO; we must decide bucket/key organization and how signed URLs are produced when the API runs inside Docker (internal host `minio:9000`) but browsers reach MinIO through a host-published address.

**Options:**

### Option A: Single private bucket, per-video key prefix, two S3 clients (internal + public endpoint)
- One bucket (`S3_BUCKET`, default `streamtube`), keys `videos/{videoId}/source` (original) and `videos/{videoId}/thumbnail.jpg`. An **internal** `S3Client` (`S3_ENDPOINT=http://minio:9000`) performs server-side calls; a **presign** `S3Client` configured with `S3_PUBLIC_ENDPOINT` signs URLs handed to clients, so the signed `Host` matches the address the client uses. Bucket is private; access only via presigned URLs. A one-shot `minio-init` Compose service creates the bucket with `mc mb --ignore-existing`. **Image note:** MinIO Inc. stopped publishing the official `minio/minio` images (pulls from Docker Hub and quay.io are denied as of 2026-11); the Compose file uses the community build `pgsty/minio:RELEASE.2026-08-04T00-00-00Z` (same MinIO server binary, ships `mc` and `curl`), pinned by tag. In production the S3 endpoint is AWS S3, so this only affects local development.
- **Pros:** Everything for a video lives under one prefix (easy cleanup in Phase 04 deletes). One bucket → one policy/CORS config. The internal/public split keeps the "use the Compose service name" rule for server-to-server traffic while producing browser-usable URLs. Same code works on AWS (both endpoints unset → AWS defaults).
- **Cons:** Two client instances to configure. Thumbnails and videos share the same lifecycle rules.

### Option B: Two buckets (`videos`, `thumbnails`), public-read thumbnails bucket
- Separate buckets; thumbnails served anonymously via a public bucket policy.
- **Pros:** Thumbnails cacheable by a CDN without signing.
- **Cons:** Public bucket is a security decision that belongs with visibility (public/unlisted is Phase 04). Two buckets to create/configure. Cleanup spans buckets.

**Recommendation:** **Option A** — single private bucket with per-video prefixes and presigned access keeps visibility decisions for Phase 04 and works unchanged on S3. Client options for MinIO: `forcePathStyle: true`, `requestChecksumCalculation: 'WHEN_REQUIRED'` and `responseChecksumValidation: 'WHEN_REQUIRED'` (AWS SDK v3 ≥ 3.729 adds CRC checksums by default, which third-party S3 implementations and presigned part URLs do not expect). Libraries: `@aws-sdk/client-s3@~3.1156.0`, `@aws-sdk/s3-request-presigner@~3.1156.0`.

**Decision:** A (Single private bucket, per-video key prefix, internal + public S3 clients)

**Libraries:** `@aws-sdk/client-s3@~3.1156.0`, `@aws-sdk/s3-request-presigner@~3.1156.0`

---

## TD-04: Video Worker Runtime and FFmpeg Integration

**Scope:** Backend

**Capability:** Transversal — covers: "Processamento automático do vídeo após upload (extração de duração e metadados)", "Geração automática de thumbnail a partir de um frame do vídeo"

**Context:** The diagram has a "Video Worker (FFmpeg)" container separate from the API. We must decide how it is packaged, how it invokes FFmpeg/ffprobe, and how it reads a 10GB object without copying it.

**Options:**

### Option A: Same NestJS codebase, separate entrypoint/container (`src/worker.ts` + `WorkerModule`), FFmpeg via `child_process.spawn`, reading the object through a presigned internal URL
- `worker.ts` boots `NestFactory.createApplicationContext(WorkerModule)` (no HTTP server). `WorkerModule` imports config, TypeORM, storage, BullMQ and the processing module whose `@Processor` consumes the queue. The `worker` Compose service reuses the dev image (FFmpeg installed in `Dockerfile.dev`). `ffprobe -print_format json -show_format -show_streams <url>` extracts metadata and `ffmpeg -ss <t> -i <url> -frames:v 1 -vf scale=640:-2 -f image2 pipe:1` grabs one JPEG frame; `<url>` is a short-lived presigned GET on the **internal** endpoint, so FFmpeg uses HTTP range requests and never downloads the whole file.
- **Pros:** Reuses entities, config, storage service and conventions (no duplicated code). Worker scales independently (`docker compose up --scale worker=N`). No temp-disk copy of 10GB files. `spawn` with an argument array (no shell) is safe and has no extra dependency.
- **Cons:** API and worker share one image (FFmpeg adds ~100MB to the API image too). Processing quality depends on the container's FFmpeg build.

### Option B: `fluent-ffmpeg` wrapper
- Same runtime as A, but FFmpeg calls through `fluent-ffmpeg`.
- **Pros:** Fluent API, built-in ffprobe JSON parsing.
- **Cons:** The package is archived/deprecated upstream (no longer maintained). Adds a dependency to wrap two commands.

### Option C: Dedicated worker in another language/image (e.g., Python + ffmpeg)
- **Pros:** Lean worker image.
- **Cons:** Duplicates DB/storage access code and entity knowledge in a second stack, violating continuity with the project patterns. BullMQ's Python client is less mature.

**Recommendation:** **Option A** — one codebase, separate process/container, plain `spawn` of the FFmpeg binaries, streaming the source via presigned URL. Thumbnail frame at `min(1s, duration/2)` scaled to 640px wide JPEG; metadata stored as `jsonb` (`format_name`, `bit_rate`, `width`, `height`, `video_codec`, `audio_codec`, `frame_rate`) plus a dedicated `duration_seconds` column.

**Decision:** A (Same codebase, separate worker entrypoint/container, FFmpeg via spawn over presigned URL)

**Libraries:** — (FFmpeg/ffprobe binaries from Debian `ffmpeg` package in `Dockerfile.dev`)

---

## TD-05: Unique Video URL Strategy

**Scope:** Backend

**Capability:** URL única por vídeo, sem conflito com outros vídeos

**Context:** Each video needs a public, stable identifier for its URL that never collides and does not leak sequence/enumeration.

**Options:**

### Option A: UUID primary key in the URL
- **Pros:** Already unique, zero extra column.
- **Cons:** Long (36 chars), ugly URLs; couples the public URL to the internal PK.

### Option B: Random short slug (11-char base64url, YouTube-style) with unique constraint + retry
- `crypto.randomBytes(8)` encoded as base64url → 11 chars (64 bits of entropy). `slug` column `varchar(11)` with a UNIQUE index; on unique violation the insert is retried with a new slug (max 5 attempts).
- **Pros:** Short, non-enumerable, decoupled from PK. The DB constraint makes uniqueness a guarantee, not a probability. Collision probability is negligible (birthday bound ~2^32 videos) and still handled.
- **Cons:** Extra column/index; retry logic needed.

### Option C: Title-based slug (`my-video-title-1234`)
- **Pros:** SEO-friendly.
- **Cons:** Titles change in Phase 04 (edit) → URL instability or redirects; collision handling for common titles.

**Recommendation:** **Option B** — short, non-guessable, stable regardless of title edits, guaranteed unique by the DB constraint. The slug is the path parameter of all `/videos/:slug` routes.

**Decision:** B (Random 11-char base64url slug + unique constraint + retry)

**Libraries:** —

---

## TD-06: Streaming and Download Delivery

**Scope:** Backend

**Capability:** Transversal — covers: "Reprodução via streaming (sem necessidade de download completo)", "Download do vídeo pelo usuário"

**Context:** Playback must start without downloading the full file (HTTP range requests / `206 Partial Content`), and users must be able to download the original file. The diagram states "Frontend → Object Storage: Streams".

**Options:**

### Option A: API proxies the bytes with Range support
- `GET /videos/:slug/stream` parses `Range`, calls `GetObject` with `Range`, pipes the body with `206`, `Content-Range`, `Accept-Ranges`.
- **Pros:** Single origin, API can meter traffic.
- **Cons:** All playback bandwidth flows through the API (the same scalability problem TD-02 avoids for uploads). Re-implements range semantics the storage already provides.

### Option B: API authorizes and redirects (`302`) to a short-lived presigned GET URL; storage serves Range/206
- `GET /videos/:slug/stream` → `302 Location: <presigned GET, inline, Content-Type of the video>`; `GET /videos/:slug/download` → `302` to a presigned GET with `ResponseContentDisposition: attachment; filename="<original name>"`; `GET /videos/:slug/thumbnail` → `302` to the thumbnail. S3/MinIO natively answer `Range` with `206 Partial Content`, so `<video src="/videos/:slug/stream">` seeks without full download.
- **Pros:** Zero media bytes through the API; matches the diagram. Range, `Accept-Ranges`, ETag/conditional requests handled by the storage (and by CloudFront in production). Authorization stays in the API (only `ready` videos are redirected).
- **Cons:** Presigned URLs are bearer links until they expire (short expiry mitigates: `STREAM_URL_EXPIRATION_SECONDS`, default 1h). Browser must reach the storage public endpoint.

### Option C: HLS/DASH transcoding (adaptive bitrate)
- Worker transcodes to HLS renditions and the player streams segments.
- **Pros:** Adaptive quality, best playback experience.
- **Cons:** Transcoding a 10GB file is CPU-heavy and far beyond the phase scope (the plan requires metadata + thumbnail only). Can be added later on top of Option B's storage layout.

**Recommendation:** **Option B** — authorization in the API, bytes and range semantics from the storage; progressive MP4/WebM playback with `206 Partial Content` satisfies "streaming sem download completo" without transcoding.

**Decision:** B (Authorize + 302 redirect to presigned GET; storage serves Range/206)

**Libraries:** `@aws-sdk/s3-request-presigner@~3.1156.0`

---

## TD-07: Video Status Lifecycle and Processing Failure Handling

**Scope:** Backend

**Capability:** Transversal — covers: "Pré-cadastro automático do vídeo como rascunho ao iniciar o upload", "Processamento automático do vídeo após upload (extração de duração e metadados)"

**Context:** The video row must reflect where it is in the pipeline, and failures (corrupt file, non-video file, FFmpeg/storage errors, oversized upload) must leave a terminal, diagnosable state.

**Options:**

### Option A: Four-state enum `draft → processing → ready | failed`, retries in the queue, terminal `failed` with reason
- `draft` on `POST /videos` (multipart open); `processing` after a successful `complete` (job enqueued with `jobId = videoId`, `attempts: 3`, exponential backoff 5s); `ready` when metadata + thumbnail are persisted; `failed` with `failure_reason` when the last attempt fails, when the file is not a video (`UnrecoverableError` → no retries), when the actual size exceeds the limit, or when enqueueing fails. The worker is idempotent: a job for a `ready` video is a no-op.
- **Pros:** Mirrors the statuses the challenge describes (rascunho → processando → pronto/erro). Transient errors retried automatically; permanent errors fail fast. `failure_reason` gives operators a diagnosis.
- **Cons:** `failed` is terminal in this phase (re-upload/reprocess flows belong to Phase 04 management).

### Option B: Fine-grained states (`uploading`, `uploaded`, `probing`, `generating_thumbnail`, …)
- **Pros:** More detailed progress.
- **Cons:** More transitions to keep consistent; the extra states carry no business rule in this phase.

**Recommendation:** **Option A** — the minimal state machine that carries all business rules of the phase. Note: `draft` here means "uploaded but not processed"; the editorial draft → published flow (visibility) is Phase 04 and will be a separate attribute.

**Decision:** A (`draft → processing → ready | failed`, queue retries, terminal `failed` with reason)

**Libraries:** `bullmq@~5.81.5`

---

## TD-08: Owner Visibility of Non-Ready Videos on Public Routes

**Scope:** Backend

**Capability:** Transversal — covers: "Pré-cadastro automático do vídeo como rascunho ao iniciar o upload", "Reprodução via streaming (sem necessidade de download completo)"

**Context:** _Added during the `plan-validate ↔ plan-resolve` loop (validation finding MD-1)._ `GET /videos/:slug` must be public (anonymous users watch freely — `CLAUDE.md` project overview), but the owner also needs to read the status of a `draft`/`processing`/`failed` video to follow processing. The global `JwtAuthGuard` (`phase-02-auth/TD-02`) returns early on `@Public()` routes without decoding the token, so a public handler cannot know who the caller is.

**Options:**

### Option A: Optional authentication on `@Public()` routes
- On `@Public()` routes the guard still never rejects, but when a well-formed `Authorization: Bearer` header carries a valid access token it attaches the payload to `request.user`; invalid/missing tokens are ignored (caller treated as anonymous). Services receive `viewerUserId?: string`.
- **Pros:** One URL per video for everyone (the "URL única"). Backward compatible: no existing public route reads `request.user`, and protected routes keep the exact same behaviour. Logic stays in the guard (infra concern) while the visibility rule lives in `VideosService`.
- **Cons:** Public routes now perform a JWT verification when a header is present (cheap HMAC).

### Option B: Separate owner-only endpoint (`GET /channels/me/videos/:slug`)
- **Pros:** No guard change.
- **Cons:** Two URLs for the same resource; channel-scoped listing/management is Phase 04's panel.

### Option C: Make `GET /videos/:slug` authenticated
- **Cons:** Breaks anonymous watching.

**Recommendation:** **Option A** — keeps a single unique URL per video and the visibility rule in the service: `ready` videos are visible to everyone; non-ready videos only to the owning channel's user (others get `404 VIDEO_NOT_FOUND`, so drafts are not disclosed).

**Decision:** A (Optional authentication on `@Public()` routes)

**Libraries:** —

---

## Decisions Summary

| ID | Scope | Decision | Recommendation | Choice |
|----|-------|----------|---------------|--------|
| TD-01 | Backend | Message Queue Technology | A (BullMQ + Redis) | A |
| TD-02 | Backend | 10GB Upload Strategy | B (Direct S3 multipart, presigned parts) | B |
| TD-03 | Backend | Object Storage Layout and S3 Client | A (Single private bucket, internal + public clients) | A |
| TD-04 | Backend | Video Worker Runtime and FFmpeg | A (Same codebase, separate container, spawn) | A |
| TD-05 | Backend | Unique Video URL | B (11-char base64url slug + unique + retry) | B |
| TD-06 | Backend | Streaming and Download Delivery | B (302 to presigned GET; storage Range/206) | B |
| TD-07 | Backend | Status Lifecycle and Failure Handling | A (draft → processing → ready/failed) | A |
| TD-08 | Backend | Owner Visibility of Non-Ready Videos on Public Routes | A (Optional auth on `@Public()` routes) | A |
