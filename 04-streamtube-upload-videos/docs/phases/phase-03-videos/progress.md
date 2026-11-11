# phase-03-videos — Progress

**Status:** completed
**SIs:** 11/11 completed

### SI-03.1 — Dependencies, Configuration Namespaces, and Compose Infrastructure
- **Status:** completed
- **Tests:** 9/9 passing (env.validation.integration-spec.ts); suítes existentes verdes
- **Observations:**
- O pull da imagem `minio/minio` foi negado no Docker Hub e no quay.io (2026-11); `minio` e `minio-init` usam `pgsty/minio:RELEASE.2026-08-04T00-00-00Z`, registrado em `phase-03-videos/TD-03`.
- O serviço `worker` compartilha o bind mount e o `node_modules` com `nestjs-api`; fica reiniciando (`restart: unless-stopped`) até o primeiro `npm install`.
- Extraídos `configModuleOptions` (`src/config/config-module.options.ts`) e `typeOrmAsyncOptions` (`src/database/typeorm-options.factory.ts`) para serem compartilhados por `AppModule` e `WorkerModule` (antecipado do SI-03.8).

### SI-03.2 — Storage Module (S3/MinIO)
- **Status:** completed
- **Tests:** 9/9 passing (storage.service.integration-spec.ts: 8 integração contra MinIO real, storage.module.spec.ts: 1 unit)
- **Observations:**
- Testes rodam dentro da rede do Compose, onde `S3_PUBLIC_ENDPOINT` (`localhost:9000`) não é alcançável; como a assinatura SigV4 embute o `Host`, os testes assinam com `http://minio:9000` via `signPresignedUrlsWithInternalEndpoint()` (`src/test/storage.ts`).

### SI-03.3 — Video Entity, Channel Relation, and Migration
- **Status:** completed
- **Tests:** 9/9 passing (video.entity.integration-spec.ts: 6, migrations.integration-spec.ts: 3)
- **Observations:**
- `migrations.integration-spec.ts` passou a dropar também os tipos enum e a executar os drops em sequência — sem isso, rodar as migrations sobre um banco já migrado falha com `type ... already exists`.
- `Video` adicionado a todos os `ALL_ENTITIES` dos specs e `DELETE FROM "videos"` primeiro em `cleanAllTables`.

### SI-03.4 — Optional Authentication on Public Routes
- **Status:** completed
- **Tests:** 9/9 passing (jwt-auth.guard.spec.ts — novos ramos de auth opcional + casos de rota protegida)
- **Observations:** none

### SI-03.5 — Upload Initiation with Draft Pre-Registration (`POST /videos`)
- **Status:** completed
- **Tests:** slug.util.spec.ts 3/3, videos.service.spec.ts (planejamento de partes, retry de slug, compensação com abort do multipart, canal inexistente), videos.service.integration-spec.ts (rascunho persistido + multipart aberto no MinIO), videos.e2e-spec.ts (`POST /videos`: 201 com 103 URLs para 10 GiB, validação, 401) — todos passando
- **Observations:** none

### SI-03.6 — Upload Completion and Job Publication
- **Status:** completed
- **Tests:** videos.service.spec.ts (guarda de status, tamanho excedido, opções do job, compensação de falha ao enfileirar), videos.service.integration-spec.ts (complete real com MinIO + Redis, job com `jobId = videoId`), videos.e2e-spec.ts (sucesso, 404 não-dono, 409 segunda conclusão, 400 ETags inválidos) — todos passando. Totais do arquivo: videos.service.spec.ts 23/23, videos.service.integration-spec.ts 4/4
- **Observations:** none

### SI-03.7 — FFmpeg Service (Probe and Thumbnail)
- **Status:** completed
- **Tests:** 13/13 passing (ffprobe.parser.spec.ts: 9 unit, ffmpeg.service.integration-spec.ts: 4 integração com binários reais e vídeo gerado com `ffmpeg -f lavfi`)
- **Observations:** none

### SI-03.8 — Video Worker (Processor, Processing Service, Entrypoint)
- **Status:** completed
- **Tests:** 20/20 passing (video.processor.spec.ts: 6, video-processing.service.spec.ts: 9, video-processing.service.integration-spec.ts: 3, worker.module.integration-spec.ts: 2)
- **Observations:**
- `WorkerModule` importa `UsersModule`: `autoLoadEntities` só conhece entidades registradas via `forFeature()`, e a cadeia `Video → Channel → User` precisa estar completa para o TypeORM montar os metadados.
- O container `worker` do Compose também consome jobs enfileirados pelos testes (mesmo Redis). Isso é esperado: os testes que precisam do resultado sobem o `WorkerModule` em processo e fazem polling do status; jobs de vídeos já apagados pela limpeza terminam como `UnrecoverableError` (`Video not found`) nos logs do worker.

### SI-03.9 — Video Read, Streaming, Download, and Thumbnail Endpoints
- **Status:** completed
- **Tests:** videos.service.spec.ts (regra de visibilidade, não pronto, thumbnail ausente) e videos.e2e-spec.ts (contratos de leitura/stream/download/thumbnail e visibilidade) — passando; videos.e2e-spec.ts 15/15
- **Observations:** none

### SI-03.10 — End-to-End Pipeline, OpenAPI Export, and AI Documentation
- **Status:** completed
- **Tests:** 2/2 passing (videos-pipeline.e2e-spec.ts: upload → fila → worker → `ready` → stream 206 → download attachment; upload não-vídeo → `failed` com motivo)
- **Observations:**
- `openapi.json` regenerado com `npm run openapi:export` (6 rotas `/videos`); a reexportação final não gerou diferença.
- Documentação de IA atualizada: `CLAUDE.md` da raiz (fila BullMQ/Redis, seção "Videos (Phase 03)"), `nestjs-project/CLAUDE.md` (serviços do Compose, comandos do worker, seção "Videos, Storage, Queue and Worker", variáveis de ambiente, execução de testes), `README.md` e `docs/diagrams/software-arch.mermaid`.
- Com duas suítes e2e de vídeos, `npm run test:e2e` em paralelo passou a falhar por contaminação do banco compartilhado (o baseline exigia `--runInBand` só por convenção). Adicionado `maxWorkers: 1` em `test/jest-e2e.json` e na config Jest do `package.json`, para que `npm test` e `npm run test:e2e` sejam seguros sem flags extras.

### SI-03.11 — Lint Baseline Correction (Definition of Done)
- **Status:** completed
- **Tests:** no tests (mudança de lint/tipos); suíte completa verde — 234/234 unit + integração (35 suítes), 69/69 e2e (5 suítes); `npx tsc --noEmit` exit 0; `npm run lint` exit 0; `npm run build` exit 0
- **Observations:**
- Override no `eslint.config.mjs` desliga apenas `no-unsafe-*`, `unbound-method` e `require-await` em arquivos de teste; o código de produção em `src/` continua com as regras de type-safety.
