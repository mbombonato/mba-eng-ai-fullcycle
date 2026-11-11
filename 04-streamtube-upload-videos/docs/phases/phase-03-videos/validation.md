---
kind: phase
name: phase-03-videos
status: clean
issue_count: 0
sources_mtime:
  docs/phases/phase-03-videos/context.md: "2026-11-09T23:54:52-03:00"
  docs/decisions/technical-decisions-phase-03-videos.md: "2026-11-09T23:39:33-03:00"
issues: []
advisories:
  - id: ADV-1
    text: "The `worker` Compose service runs `npm run start:worker` and depends on `node_modules` installed by `docker compose exec nestjs-api npm install` (shared bind mount). On a fresh clone it restarts (restart: unless-stopped) until dependencies are installed — documented in nestjs-project/CLAUDE.md."
  - id: ADV-2
    text: "Abandoned multipart uploads (drafts never completed) are not cleaned by the API in this phase; production buckets should set an AbortIncompleteMultipartUpload lifecycle rule. Draft cleanup/deletion belongs to Phase 04 video management."
---

# phase-03-videos — Validation

## Findings

### Inconsistencies

_None._

### Ambiguities

_None._

### Missing Decisions

_None._

### Dependency Gaps

_None._

### Inherited Constraint Conflicts

_None._

### Unresolved Open Questions

_None._

### UI Coverage Gaps

_None._ (`next-frontend/` deferred for this phase — see context.md § Non-UI / Deferred Capabilities.)

## Resolved Issues

Issues found and resolved during planning. The resolutions are recorded in TD-08, TD-03, TD-04 and TD-07.

| ID | Category | Finding | Resolution |
|----|----------|-----------------|------------|
| MD-1 | Missing Decision | Public `GET /videos/:slug` must let the owner see `draft`/`processing`/`failed` videos, but the global `JwtAuthGuard` (`phase-02-auth/TD-02`) skips token decoding on `@Public()` routes — no decision defined how a public handler identifies the owner. | New `phase-03-videos/TD-08` (Option A — optional authentication on `@Public()` routes) added to the decisions doc; context.md Decisions Index and Capability Coverage updated. |
| ICC-1 | Inherited Constraint Conflict | `CLAUDE.md` requires Compose service names as hosts (`minio:9000`), but presigned URLs handed to browsers must use a host-reachable address; signing with `minio:9000` would produce URLs the client cannot open, and rewriting the host breaks the SigV4 signature. | Clarified in `phase-03-videos/TD-03`: server-to-server calls use `S3_ENDPOINT=http://minio:9000` (rule respected); a separate presign client signs with `S3_PUBLIC_ENDPOINT` (client-facing address). Tests running inside the Compose network sign with `http://minio:9000`. |
| DG-1 | Dependency Gap | TD-04 requires `ffmpeg`/`ffprobe` binaries, but `nestjs-project/Dockerfile.dev` (`node:25.6.0-slim`) does not include them; integration tests of the worker would fail. | Plan SI-03.1 installs the Debian `ffmpeg` package in `Dockerfile.dev` (shared by `nestjs-api` and `worker`). |
| AMB-1 | Ambiguity | "Pré-cadastro como rascunho" vs. Phase 04 "fluxo de rascunho → publicação": unclear whether the Phase 03 `draft` status is the editorial draft. | Clarified in `phase-03-videos/TD-07`: Phase 03 `status` is the processing lifecycle (`draft → processing → ready/failed`); the editorial publish/visibility flow is a separate attribute owned by Phase 04. |
