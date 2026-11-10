---
kind: phase
name: phase-03-videos
sources_mtime:
  docs/project-plan.md: "2026-11-09T16:25:30-03:00"
  docs/decisions/technical-decisions-phase-03-videos.md: "2026-11-09T23:39:33-03:00"
  docs/decisions/technical-decisions-phase-02-auth.md: "2026-11-09T16:25:30-03:00"
  docs/decisions/technical-decisions-phase-01-configuracao-base.md: "2026-11-09T16:25:30-03:00"
  docs/phases/phase-02-auth/phase-02-auth.md: "2026-11-09T16:25:30-03:00"
  docs/phases/phase-03-videos/library-refs.md: "2026-11-09T23:54:52-03:00"
---

# phase-03-videos — Context

## Scope

**Phase name:** Fase 03 — Upload e Processamento de Vídeos

**Capabilities**

- Serviço de armazenamento de arquivos (vídeos e thumbnails)
- Serviço de processamento em segundo plano (filas)
- Upload de vídeos com suporte a arquivos de até 10GB sem impacto na performance
- Pré-cadastro automático do vídeo como rascunho ao iniciar o upload
- Processamento automático do vídeo após upload (extração de duração e metadados)
- Geração automática de thumbnail a partir de um frame do vídeo
- URL única por vídeo, sem conflito com outros vídeos
- Reprodução via streaming (sem necessidade de download completo)
- Download do vídeo pelo usuário

**Out of scope:** edição de informações do vídeo, categorias, visibilidade público/unlisted, fluxo rascunho → publicação editorial e painel do canal (Fase 04); página de visualização/player (Fase 05); interações sociais (Fase 06); transcodificação adaptativa (HLS/DASH).

**Deliverables:** upload de até 10GB funcional, processamento automático do vídeo, streaming funcionando, URLs únicas geradas.

**Affected subprojects:** `nestjs-project/`

**Deferred subprojects:** `next-frontend/` — o enunciado do desafio da Fase 03 declara que "a interface de vídeo não faz parte do escopo desta fase"; as telas de upload/player ficam para as fases que as possuem.

**Sequencing notes:** Depends on Fase 01 — Configuração Base and Fase 02 — Cadastro, Login e Gerenciamento de Conta (each user owns exactly one channel; videos belong to a channel).

**Neighbors (for boundary detection only):** Fase 02 (prior), Fase 04 — Gerenciamento de Vídeos e Canal (next).

## Decisions Index

| Ref | Source | Scope | Topic | Status | Decision | Libraries |
|-----|--------|-------|-------|--------|----------|-----------|
| phase-03-videos/TD-01 | technical-decisions-phase-03-videos.md | Backend | Message Queue Technology | decided | A (BullMQ + Redis) | bullmq@~5.81.5, @nestjs/bullmq@^11.0.5 |
| phase-03-videos/TD-02 | technical-decisions-phase-03-videos.md | Backend | 10GB Upload Strategy | decided | B (Direct S3 multipart with presigned part URLs) | @aws-sdk/client-s3@~3.1156.0, @aws-sdk/s3-request-presigner@~3.1156.0 |
| phase-03-videos/TD-03 | technical-decisions-phase-03-videos.md | Backend | Object Storage Layout and S3 Client | decided | A (Single private bucket, internal + public clients) | @aws-sdk/client-s3@~3.1156.0, @aws-sdk/s3-request-presigner@~3.1156.0 |
| phase-03-videos/TD-04 | technical-decisions-phase-03-videos.md | Backend | Video Worker Runtime and FFmpeg | decided | A (Same codebase, separate container, spawn over presigned URL) | — (ffmpeg Debian package) |
| phase-03-videos/TD-05 | technical-decisions-phase-03-videos.md | Backend | Unique Video URL | decided | B (11-char base64url slug + unique + retry) | — |
| phase-03-videos/TD-06 | technical-decisions-phase-03-videos.md | Backend | Streaming and Download Delivery | decided | B (302 to presigned GET; storage Range/206) | @aws-sdk/s3-request-presigner@~3.1156.0 |
| phase-03-videos/TD-07 | technical-decisions-phase-03-videos.md | Backend | Status Lifecycle and Failure Handling | decided | A (draft → processing → ready/failed) | bullmq@~5.81.5 |
| phase-03-videos/TD-08 | technical-decisions-phase-03-videos.md | Backend | Owner Visibility of Non-Ready Videos on Public Routes | decided | A (Optional auth on `@Public()` routes) | — |

_Source files:_

- `docs/decisions/technical-decisions-phase-03-videos.md`

## Capability Coverage

| Capability | Covered by |
|------------|------------|
| Serviço de armazenamento de arquivos (vídeos e thumbnails) | phase-03-videos/TD-03 |
| Serviço de processamento em segundo plano (filas) | phase-03-videos/TD-01, phase-03-videos/TD-04 |
| Upload de vídeos com suporte a arquivos de até 10GB sem impacto na performance | phase-03-videos/TD-02 |
| Pré-cadastro automático do vídeo como rascunho ao iniciar o upload | phase-03-videos/TD-02, phase-03-videos/TD-07, phase-03-videos/TD-08 |
| Processamento automático do vídeo após upload (extração de duração e metadados) | phase-03-videos/TD-04, phase-03-videos/TD-07 |
| Geração automática de thumbnail a partir de um frame do vídeo | phase-03-videos/TD-04 |
| URL única por vídeo, sem conflito com outros vídeos | phase-03-videos/TD-05 |
| Reprodução via streaming (sem necessidade de download completo) | phase-03-videos/TD-06, phase-03-videos/TD-08 |
| Download do vídeo pelo usuário | phase-03-videos/TD-06 |

## Decisions Detail

### phase-03-videos/TD-01

**Recommendation:** Option A (BullMQ + Redis) — first-class NestJS integration and native retry/backoff/dedup semantics; Redis is a trivial container matching the diagram's separate "Message Queue". Pin `bullmq@~5.81.5` (mature 5.x line; 6.0.0 removed Redis internals and made `ioredis` an optional peer) with `@nestjs/bullmq@^11.0.5`.

**Libraries:** `bullmq@~5.81.5`, `@nestjs/bullmq@^11.0.5`

### phase-03-videos/TD-02

**Recommendation:** Option B — the API never touches video bytes. `POST /videos` opens the multipart upload, pre-registers the draft and returns presigned part URLs; the client completes via `POST /videos/:slug/upload/complete`. Part size `UPLOAD_PART_SIZE_MB` (100 MiB), max size constant `VIDEO_MAX_FILE_SIZE_BYTES` (10 GiB), URL expiry `UPLOAD_URL_EXPIRATION_SECONDS` (24h). Actual size re-checked with `HeadObject`.

**Libraries:** `@aws-sdk/client-s3@~3.1156.0`, `@aws-sdk/s3-request-presigner@~3.1156.0`

### phase-03-videos/TD-03

**Recommendation:** Option A — single private bucket (`S3_BUCKET`), keys `videos/{videoId}/source` and `videos/{videoId}/thumbnail.jpg`; internal client on `S3_ENDPOINT` (`http://minio:9000`) and presign client on `S3_PUBLIC_ENDPOINT`; `forcePathStyle: true`, checksums `WHEN_REQUIRED`; bucket created by a one-shot `minio-init` Compose service; image `pgsty/minio:RELEASE.2026-08-04T00-00-00Z` (official `minio/minio` images no longer published).

**Libraries:** `@aws-sdk/client-s3@~3.1156.0`, `@aws-sdk/s3-request-presigner@~3.1156.0`

### phase-03-videos/TD-04

**Recommendation:** Option A — `src/worker.ts` boots `NestFactory.createApplicationContext(WorkerModule)`; `worker` Compose service reuses the dev image with FFmpeg; `ffprobe`/`ffmpeg` via `child_process.spawn` (no shell) reading a presigned internal GET URL (HTTP range, no full download). Thumbnail at `min(1s, duration/2)`, 640px JPEG. Metadata in `jsonb` + `duration_seconds`.

**Libraries:** — (FFmpeg/ffprobe binaries)

### phase-03-videos/TD-05

**Recommendation:** Option B — `crypto.randomBytes(8)` → 11-char base64url slug, UNIQUE index, retry on unique violation (max 5). Slug is the path parameter of `/videos/:slug` routes.

**Libraries:** —

### phase-03-videos/TD-06

**Recommendation:** Option B — `GET /videos/:slug/stream`, `/download`, `/thumbnail` authorize and answer `302` to a short-lived presigned GET (`STREAM_URL_EXPIRATION_SECONDS`, 1h); storage answers `Range` with `206 Partial Content`. Download uses `ResponseContentDisposition: attachment`.

**Libraries:** `@aws-sdk/s3-request-presigner@~3.1156.0`

### phase-03-videos/TD-07

**Recommendation:** Option A — `draft` (upload open) → `processing` (upload completed, job enqueued with `jobId = videoId`, 3 attempts, exponential backoff 5s) → `ready` | `failed` (+ `failure_reason`). Non-video input → `UnrecoverableError` (no retry). Worker idempotent.

**Libraries:** `bullmq@~5.81.5`

### phase-03-videos/TD-08

**Recommendation:** Option A — the global guard attaches `request.user` on `@Public()` routes when a valid bearer token is present and ignores invalid/missing tokens. `ready` videos visible to all; non-ready only to the owner (others: `404 VIDEO_NOT_FOUND`).

**Libraries:** —

## Inherited Decisions Detail

### phase-01-configuracao-base/TD-01 … TD-04

**Recommendation:** `@nestjs/config` with namespaced `registerAs` factories validated by a Joi schema; the same factory is importable by non-DI code (TypeORM CLI data source).

**Libraries:** `@nestjs/config@^4.x`, `joi`

### phase-02-auth/TD-02

**Recommendation (as decided):** custom `JwtAuthGuard` with `@nestjs/jwt`, registered as `APP_GUARD`; every route protected unless `@Public()`. TD-08 of this phase extends its `@Public()` branch (optional authentication) without changing protected-route behaviour.

**Libraries:** `@nestjs/jwt@^11.0.0`

### phase-02-auth/TD-06

**Recommendation:** class-validator + class-transformer DTOs with the global `ValidationPipe` (`whitelist`, `forbidNonWhitelisted`, `transform`).

**Libraries:** `class-validator@^0.14.x`, `class-transformer@^0.5.x`

### phase-02-auth/TD-07

**Recommendation:** domain exceptions (`DomainException` subclasses) mapped by `DomainExceptionFilter` to `{ statusCode, error, message }`; validation errors → `VALIDATION_ERROR`.

**Libraries:** —

## Inherited Conventions

- Config: one `registerAs` file per domain in `src/config/`, every new env var added to `env.validation.ts` and `.env.example`. _(from phase 01)_
- Every service is reached by its Compose service name inside Docker (`db`, `minio`, `redis`), never `localhost`. _(from CLAUDE.md)_
- Entities: explicit table name, UUID PK, `created_at`/`updated_at`, both sides of relations, registered in the owning module's `TypeOrmModule.forFeature`. _(from .claude/rules/nestjs-entities.md, nestjs-modules.md)_
- Migrations generated by the TypeORM CLI, never `synchronize`; migration tests restore the schema in `afterAll`. _(from .claude/rules/typeorm-migrations.md)_
- Services throw `DomainException` subclasses (never HTTP exceptions); controllers are thin, documented with `@nestjs/swagger` and `ApiErrorEnvelope`. _(from .claude/rules/nestjs-services.md, nestjs-controllers.md)_
- Background tasks (queue consumers) may catch-and-log instead of rethrowing only at the job boundary. _(from .claude/rules/nestjs-services.md)_
- Test suffixes `*.spec.ts` / `*.integration-spec.ts` / `*.e2e-spec.ts`; integration/e2e run `--runInBand` against the real Compose services. _(from nestjs-project/CLAUDE.md)_

## Inherited Deferred Capabilities

| Capability | Origin | Status |
|------------|--------|--------|
| Telas de cadastro, login, confirmação de conta e recuperação de senha | Fase 02 | Delivered later in `phase-02-auth-frontend` — no impact on this phase. |

## Non-UI / Deferred Capabilities

| Capability | Status | Rationale | TD refs |
|------------|--------|-----------|---------|
| Interface de upload/player de vídeo | deferred | Declared out of scope for Phase 03 by the challenge statement; owned by Fases 04/05. | — |

## Testing Requirements

Refer to the `testing-guide-nestjs-project` Skill for layer requirements per artifact type in `nestjs-project/`. Phase 03 adds infrastructure that must be exercised for real, not mocked, in integration/e2e tests: MinIO (storage service integration tests and e2e multipart upload through presigned URLs), Redis/BullMQ (producer enqueues, worker consumes in-process in e2e), FFmpeg (probe + thumbnail integration tests on a video generated at test time with `ffmpeg -f lavfi`). Unit tests cover pure logic (slug generation, ffprobe output parsing, part planning, processor retry/failure branching, guard optional-auth branch). Specific layer coverage per SI is recorded in `progress.md`.
