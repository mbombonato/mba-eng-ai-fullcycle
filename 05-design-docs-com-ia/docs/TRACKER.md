# Tracker de Rastreabilidade — Sistema de Webhooks de Notificação de Pedidos

Cada linha liga um item identificado nos documentos (`PRD`, `RFC`, `FDD`, `ADRs`) à sua origem: um trecho da reunião (`TRANSCRICAO`, no formato `[hh:mm] Nome`) ou um arquivo real do repositório (`CODIGO`). Quando um item tem várias origens, a coluna **Localização** aponta a fala ou o arquivo **principal**; as demais aparecem no próprio documento.

Os IDs `ADR-NNN-ALT-NN` e `ADR-NNN-CONS-NN` seguem a ordem das linhas da tabela de alternativas e dos blocos de consequências de cada ADR.

Itens marcados como "proposta de implementação" no FDD também aparecem aqui, ligados à fala ou ao arquivo de onde foram derivados.

| ID | Documento | Tipo | Conteúdo (resumo) | Fonte | Localização |
| --- | --- | --- | --- | --- | --- |
| PRD-CEN-01 | `docs/PRD.md` | Cenário de uso | Cliente filtra notificações para `SHIPPED` e `DELIVERED` | TRANSCRICAO | [09:33] Marcos |
| PRD-CEN-02 | `docs/PRD.md` | Cenário de uso | Indisponibilidade de 2 h do cliente coberta por retry | TRANSCRICAO | [09:16] Diego |
| PRD-CEN-03 | `docs/PRD.md` | Cenário de uso | Suporte consulta histórico das últimas entregas | TRANSCRICAO | [09:34] Marcos |
| PRD-CEN-04 | `docs/PRD.md` | Cenário de uso | Cliente vaza secret e rotaciona com 24 h de convivência | TRANSCRICAO | [09:22] Diego |
| PRD-CEN-05 | `docs/PRD.md` | Cenário de uso | ADMIN reprocessa notificação da DLQ | TRANSCRICAO | [09:18] Diego |
| PRD-OBJ-01 | `docs/PRD.md` | Objetivo / métrica | p95 < 10 s entre mudança de status e 1ª tentativa | TRANSCRICAO | [09:02] Marcos |
| PRD-OBJ-02 | `docs/PRD.md` | Objetivo / métrica | 3 de 3 clientes (Atlas, MaxDistribuição, Nova Cargo) ativos até fim de novembro | TRANSCRICAO | [09:45] Marcos |
| PRD-OBJ-03 | `docs/PRD.md` | Objetivo / métrica | Zero mudanças de status sem evento registrado | TRANSCRICAO | [09:40] Bruno |
| PRD-OBJ-04 | `docs/PRD.md` | Objetivo / métrica | Janela de ~15 h coberta por retentativas | TRANSCRICAO | [09:17] Diego |
| PRD-OBJ-05 | `docs/PRD.md` | Objetivo / métrica | Entrega em 3 sprints incluindo revisão de segurança | TRANSCRICAO | [09:47] Larissa |
| PRD-OOS-01 | `docs/PRD.md` | Fora de escopo (adiado) | E-mail ao cliente quando webhook falha | TRANSCRICAO | [09:37] Larissa |
| PRD-OOS-02 | `docs/PRD.md` | Fora de escopo (descartado) | Dashboard visual para o cliente | TRANSCRICAO | [09:40] Larissa |
| PRD-OOS-03 | `docs/PRD.md` | Fora de escopo (adiado) | Rate limiting de envio — observar e decidir depois | TRANSCRICAO | [09:39] Larissa |
| PRD-OOS-04 | `docs/PRD.md` | Fora de escopo (descartado) | Webhooks inbound | TRANSCRICAO | [09:02] Marcos |
| PRD-OOS-05 | `docs/PRD.md` | Fora de escopo (adiado) | Ordenação global e múltiplos workers | TRANSCRICAO | [09:13] Larissa |
| PRD-OOS-06 | `docs/PRD.md` | Fora de escopo | Arquivamento de linhas entregues após ~30 dias | TRANSCRICAO | [09:08] Diego |
| PRD-OOS-07 | `docs/PRD.md` | Fora de escopo (descartado) | Itens do pedido no payload | TRANSCRICAO | [09:43] Diego |
| PRD-OOS-08 | `docs/PRD.md` | Fora de escopo (descartado) | Garantia exactly-once | TRANSCRICAO | [09:25] Diego |
| PRD-FR-01 | `docs/PRD.md` | Requisito Funcional | Notificar o cliente via POST a cada mudança de status | TRANSCRICAO | [09:00] Marcos |
| PRD-FR-02 | `docs/PRD.md` | Requisito Funcional | Cadastrar webhook com URL, customer_id e status; customer_id não vem do JWT | TRANSCRICAO | [09:32] Larissa |
| PRD-FR-03 | `docs/PRD.md` | Requisito Funcional | Secret gerada pela plataforma e devolvida na criação | TRANSCRICAO | [09:31] Marcos |
| PRD-FR-04 | `docs/PRD.md` | Requisito Funcional | Listar, editar e remover webhooks | TRANSCRICAO | [09:33] Bruno |
| PRD-FR-05 | `docs/PRD.md` | Requisito Funcional | Filtro de status por webhook | TRANSCRICAO | [09:33] Marcos |
| PRD-FR-06 | `docs/PRD.md` | Requisito Funcional | Histórico das últimas 100 entregas por webhook | TRANSCRICAO | [09:34] Marcos |
| PRD-FR-07 | `docs/PRD.md` | Requisito Funcional | Reenvio automático em 1m/5m/30m/2h/12h | TRANSCRICAO | [09:17] Larissa |
| PRD-FR-08 | `docs/PRD.md` | Requisito Funcional | DLQ com motivo da falha após esgotar tentativas | TRANSCRICAO | [09:18] Diego |
| PRD-FR-09 | `docs/PRD.md` | Requisito Funcional | Replay manual da DLQ por ADMIN com registro de autoria | TRANSCRICAO | [09:36] Sofia |
| PRD-FR-10 | `docs/PRD.md` | Requisito Funcional | Assinatura HMAC-SHA256 de cada notificação | TRANSCRICAO | [09:20] Sofia |
| PRD-FR-11 | `docs/PRD.md` | Requisito Funcional | Rotação de secret via API com 24 h de grace period | TRANSCRICAO | [09:21] Sofia |
| PRD-FR-12 | `docs/PRD.md` | Requisito Funcional | Headers `X-Event-Id` e `X-Webhook-Id` | TRANSCRICAO | [09:44] Sofia |
| PRD-FR-13 | `docs/PRD.md` | Requisito Funcional | Payload com dados essenciais em snapshot, sem itens | TRANSCRICAO | [09:43] Diego |
| PRD-NFR-01 | `docs/PRD.md` | Requisito Não Funcional | Latência < 10 s; ciclo de 2 s | TRANSCRICAO | [09:10] Larissa |
| PRD-NFR-02 | `docs/PRD.md` | Requisito Não Funcional | Consistência entre status e evento; falha do cliente não faz rollback | TRANSCRICAO | [09:04] Bruno |
| PRD-NFR-03 | `docs/PRD.md` | Requisito Não Funcional | Somente URLs https | TRANSCRICAO | [09:23] Sofia |
| PRD-NFR-04 | `docs/PRD.md` | Requisito Não Funcional | Secret por webhook, nunca global | TRANSCRICAO | [09:21] Sofia |
| PRD-NFR-05 | `docs/PRD.md` | Requisito Não Funcional | Limite de 64 KB, erro sem truncar | TRANSCRICAO | [09:24] Larissa |
| PRD-NFR-06 | `docs/PRD.md` | Requisito Não Funcional | Timeout de 10 s por tentativa | TRANSCRICAO | [09:42] Diego |
| PRD-NFR-07 | `docs/PRD.md` | Requisito Não Funcional | At-least-once com dedup por `X-Event-Id` | TRANSCRICAO | [09:26] Larissa |
| PRD-NFR-08 | `docs/PRD.md` | Requisito Não Funcional | Envio em processo separado da API | TRANSCRICAO | [09:11] Diego |
| PRD-NFR-09 | `docs/PRD.md` | Requisito Não Funcional | Ordenação só por pedido e com worker único | TRANSCRICAO | [09:13] Larissa |
| PRD-NFR-10 | `docs/PRD.md` | Requisito Não Funcional | Reuso dos padrões do projeto, sem infra nova | TRANSCRICAO | [09:30] Larissa |
| PRD-DEC-01 | `docs/PRD.md` | Decisão / Trade-off | Outbox no MySQL na mesma transação | TRANSCRICAO | [09:08] Larissa |
| PRD-DEC-02 | `docs/PRD.md` | Decisão / Trade-off | Worker separado com polling de 2 s | TRANSCRICAO | [09:10] Larissa |
| PRD-DEC-03 | `docs/PRD.md` | Decisão / Trade-off | 5 retentativas em ~15 h e DLQ; atraso aceito pelo produto | TRANSCRICAO | [09:17] Marcos |
| PRD-DEC-04 | `docs/PRD.md` | Decisão / Trade-off | HMAC-SHA256, secret por webhook, rotação 24 h | TRANSCRICAO | [09:22] Sofia |
| PRD-DEC-05 | `docs/PRD.md` | Decisão / Trade-off | At-least-once; cliente deduplica | TRANSCRICAO | [09:26] Marcos |
| PRD-DEC-06 | `docs/PRD.md` | Decisão / Trade-off | Reuso dos padrões do projeto | TRANSCRICAO | [09:30] Larissa |
| PRD-DEC-07 | `docs/PRD.md` | Decisão / Trade-off | Payload enxuto em snapshot, filtrado na inserção | TRANSCRICAO | [09:52] Larissa |
| PRD-DEP-01 | `docs/PRD.md` | Dependência | Revisão de segurança da Sofia (2 dias úteis) | TRANSCRICAO | [09:46] Sofia |
| PRD-DEP-02 | `docs/PRD.md` | Dependência | Portal do desenvolvedor atualizado por Marcos | TRANSCRICAO | [09:40] Marcos |
| PRD-DEP-03 | `docs/PRD.md` | Dependência | Confirmação de prazo com a Atlas | TRANSCRICAO | [09:47] Marcos |
| PRD-DEP-04 | `docs/PRD.md` | Dependência | Cliente com HTTPS, validação HMAC e dedup | TRANSCRICAO | [09:20] Sofia |
| PRD-DEP-05 | `docs/PRD.md` | Dependência | `PATCH /orders/:id/status` como gatilho único | CODIGO | `src/modules/orders/order.routes.ts` |
| PRD-RISK-01 | `docs/PRD.md` | Risco | Prazo de 3 sprints x fim de novembro | TRANSCRICAO | [09:46] Larissa |
| PRD-RISK-02 | `docs/PRD.md` | Risco | Cliente processa duplicatas | TRANSCRICAO | [09:25] Sofia |
| PRD-RISK-03 | `docs/PRD.md` | Risco | Vazamento de secret | TRANSCRICAO | [09:22] Diego |
| PRD-RISK-04 | `docs/PRD.md` | Risco | Cliente bombardeado por muitas notificações | TRANSCRICAO | [09:38] Diego |
| PRD-RISK-05 | `docs/PRD.md` | Risco | Notificações fora de ordem ao escalar | TRANSCRICAO | [09:13] Larissa |
| PRD-CA-01 | `docs/PRD.md` | Critério de aceitação | Notificação de `SHIPPED` em < 10 s | TRANSCRICAO | [09:02] Marcos |
| PRD-CA-02 | `docs/PRD.md` | Critério de aceitação | Status fora do filtro não notifica | TRANSCRICAO | [09:34] Bruno |
| PRD-CA-03 | `docs/PRD.md` | Critério de aceitação | URL http recusada | TRANSCRICAO | [09:23] Sofia |
| PRD-CA-04 | `docs/PRD.md` | Critério de aceitação | Secret devolvida na criação e assinatura válida | TRANSCRICAO | [09:31] Marcos |
| PRD-CA-05 | `docs/PRD.md` | Critério de aceitação | Retry 1m/5m/30m/2h/12h e depois DLQ | TRANSCRICAO | [09:17] Larissa |
| PRD-CA-06 | `docs/PRD.md` | Critério de aceitação | Replay só por ADMIN, com log do usuário | TRANSCRICAO | [09:36] Larissa |
| PRD-CA-07 | `docs/PRD.md` | Critério de aceitação | Secret antiga válida por 24 h após rotação | TRANSCRICAO | [09:21] Sofia |
| PRD-CA-08 | `docs/PRD.md` | Critério de aceitação | Histórico com últimas 100 tentativas | TRANSCRICAO | [09:34] Marcos |
| PRD-CA-09 | `docs/PRD.md` | Critério de aceitação | Falha no registro do evento impede a mudança de status | TRANSCRICAO | [09:41] Diego |
| PRD-TST-01 | `docs/PRD.md` | Estratégia de teste | Testes de integração Vitest + Supertest | CODIGO | `tests/orders.test.ts` |
| PRD-TST-02 | `docs/PRD.md` | Estratégia de teste | Worker contra servidor HTTP falso (500, >10 s, >64 KB) | TRANSCRICAO | [09:42] Diego |
| PRD-TST-03 | `docs/PRD.md` | Estratégia de teste | Revisão de segurança dedicada | TRANSCRICAO | [09:46] Sofia |
| PRD-TST-04 | `docs/PRD.md` | Estratégia de teste | Revisão do design com Bruno e Diego antes de codar | TRANSCRICAO | [09:50] Larissa |
| PRD-TST-05 | `docs/PRD.md` | Estratégia de teste | Métricas pós-lançamento alimentam decisões adiadas | TRANSCRICAO | [09:39] Larissa |
| RFC-PROP-01 | `docs/RFC.md` | Proposta | Captura transacional via outbox + `publishWebhookEvent(tx, …)` | TRANSCRICAO | [09:41] Bruno |
| RFC-PROP-02 | `docs/RFC.md` | Proposta | Worker separado, mesma stack, PrismaClient próprio, polling 2 s | TRANSCRICAO | [09:11] Diego |
| RFC-PROP-03 | `docs/RFC.md` | Proposta | Timeout 10 s, 5 retentativas, DLQ, at-least-once | TRANSCRICAO | [09:48] Larissa |
| RFC-PROP-04 | `docs/RFC.md` | Proposta | https, HMAC-SHA256, secret por endpoint, 64 KB | TRANSCRICAO | [09:22] Sofia |
| RFC-PROP-05 | `docs/RFC.md` | Proposta | Módulo `src/modules/webhooks` nos padrões do projeto | TRANSCRICAO | [09:27] Bruno |
| RFC-ALT-01 | `docs/RFC.md` | Alternativa descartada | Disparo síncrono em `changeStatus` | TRANSCRICAO | [09:04] Bruno |
| RFC-ALT-02 | `docs/RFC.md` | Alternativa descartada | Redis Streams / fila externa | TRANSCRICAO | [09:07] Diego |
| RFC-ALT-03 | `docs/RFC.md` | Alternativa descartada | Trigger de banco para acordar o worker | TRANSCRICAO | [09:09] Diego |
| RFC-ALT-04 | `docs/RFC.md` | Alternativa descartada | Retry indefinido ou só 3 tentativas | TRANSCRICAO | [09:16] Diego |
| RFC-ALT-05 | `docs/RFC.md` | Alternativa descartada | Exactly-once | TRANSCRICAO | [09:25] Diego |
| RFC-ALT-06 | `docs/RFC.md` | Alternativa descartada | Secret global | TRANSCRICAO | [09:21] Sofia |
| RFC-QA-01 | `docs/RFC.md` | Questão em aberto | Rate limiting de saída | TRANSCRICAO | [09:39] Diego |
| RFC-QA-02 | `docs/RFC.md` | Questão em aberto | E-mail de alerta ao cliente | TRANSCRICAO | [09:37] Larissa |
| RFC-QA-03 | `docs/RFC.md` | Questão em aberto | Escala para múltiplos workers | TRANSCRICAO | [09:13] Diego |
| RFC-QA-04 | `docs/RFC.md` | Questão em aberto | Endurecer permissões do CRUD | TRANSCRICAO | [09:37] Sofia |
| RFC-QA-05 | `docs/RFC.md` | Questão em aberto | Arquivamento da outbox | TRANSCRICAO | [09:08] Diego |
| RFC-QA-06 | `docs/RFC.md` | Questão em aberto | Interação entre ordenação e retry | TRANSCRICAO | [09:12] Diego |
| RFC-QA-07 | `docs/RFC.md` | Questão em aberto | Contagem de tentativas (1 + 5) | TRANSCRICAO | [09:17] Diego |
| RFC-QA-08 | `docs/RFC.md` | Questão em aberto | Armazenamento da secret e assinatura no grace period | TRANSCRICAO | [09:46] Sofia |
| RFC-QA-09 | `docs/RFC.md` | Questão em aberto | `customer_id` no body ou no path | TRANSCRICAO | [09:32] Larissa |
| RFC-RISK-01 | `docs/RFC.md` | Risco | Falha na outbox bloqueia mudança de status | TRANSCRICAO | [09:40] Bruno |
| RFC-RISK-02 | `docs/RFC.md` | Risco | Worker parado acumula eventos | TRANSCRICAO | [09:11] Diego |
| RFC-RISK-03 | `docs/RFC.md` | Risco | Cliente não deduplica | TRANSCRICAO | [09:25] Sofia |
| RFC-RISK-04 | `docs/RFC.md` | Risco | Vazamento de secret | TRANSCRICAO | [09:22] Diego |
| RFC-RISK-05 | `docs/RFC.md` | Risco | Prazo da Atlas x 3 sprints | TRANSCRICAO | [09:45] Marcos |
| ADR-001 | `docs/adrs/ADR-001-outbox-transacional-no-mysql.md` | Decisão | Outbox transacional no MySQL existente | TRANSCRICAO | [09:08] Larissa |
| ADR-001-CTX-01 | `docs/adrs/ADR-001-outbox-transacional-no-mysql.md` | Contexto (código) | Transação de `changeStatus` atualiza orders, history e estoque | CODIGO | `src/modules/orders/order.service.ts` |
| ADR-001-ALT-01 | `docs/adrs/ADR-001-outbox-transacional-no-mysql.md` | Alternativa descartada | Disparo síncrono | TRANSCRICAO | [09:06] Diego |
| ADR-001-ALT-02 | `docs/adrs/ADR-001-outbox-transacional-no-mysql.md` | Alternativa descartada | Redis Streams | TRANSCRICAO | [09:07] Larissa |
| ADR-001-CONS-01 | `docs/adrs/ADR-001-outbox-transacional-no-mysql.md` | Trade-off | Mais um INSERT na transação; arquivamento fora do escopo | TRANSCRICAO | [09:08] Diego |
| ADR-002 | `docs/adrs/ADR-002-worker-separado-com-polling.md` | Decisão | Worker separado com polling de 2 s, single-worker | TRANSCRICAO | [09:10] Larissa |
| ADR-002-DEC-01 | `docs/adrs/ADR-002-worker-separado-com-polling.md` | Decisão | Entry-point `src/worker.ts` e `npm run worker` | TRANSCRICAO | [09:11] Larissa |
| ADR-002-DEC-02 | `docs/adrs/ADR-002-worker-separado-com-polling.md` | Decisão | PrismaClient próprio, mesma DATABASE_URL | TRANSCRICAO | [09:30] Bruno |
| ADR-002-ALT-01 | `docs/adrs/ADR-002-worker-separado-com-polling.md` | Alternativa descartada | Trigger no banco | TRANSCRICAO | [09:09] Bruno |
| ADR-002-ALT-02 | `docs/adrs/ADR-002-worker-separado-com-polling.md` | Alternativa descartada | Worker dentro do processo da API | TRANSCRICAO | [09:11] Diego |
| ADR-002-ALT-03 | `docs/adrs/ADR-002-worker-separado-com-polling.md` | Alternativa descartada | Múltiplos workers em paralelo | TRANSCRICAO | [09:13] Diego |
| ADR-002-CONS-01 | `docs/adrs/ADR-002-worker-separado-com-polling.md` | Trade-off | Ordenação global não garantida; clientes não pediram | TRANSCRICAO | [09:14] Marcos |
| ADR-003 | `docs/adrs/ADR-003-retry-com-backoff-exponencial-e-dlq.md` | Decisão | Backoff 1m/5m/30m/2h/12h, 5 tentativas, DLQ separada | TRANSCRICAO | [09:17] Larissa |
| ADR-003-DEC-01 | `docs/adrs/ADR-003-retry-com-backoff-exponencial-e-dlq.md` | Decisão | Replay manual via endpoint admin | TRANSCRICAO | [09:18] Diego |
| ADR-003-ALT-01 | `docs/adrs/ADR-003-retry-com-backoff-exponencial-e-dlq.md` | Alternativa descartada | Retry indefinido | TRANSCRICAO | [09:15] Diego |
| ADR-003-ALT-02 | `docs/adrs/ADR-003-retry-com-backoff-exponencial-e-dlq.md` | Alternativa descartada | Apenas 3 tentativas | TRANSCRICAO | [09:16] Bruno |
| ADR-003-ALT-03 | `docs/adrs/ADR-003-retry-com-backoff-exponencial-e-dlq.md` | Alternativa descartada | Marcar `failed` na própria outbox | TRANSCRICAO | [09:17] Larissa |
| ADR-003-CONS-01 | `docs/adrs/ADR-003-retry-com-backoff-exponencial-e-dlq.md` | Trade-off | Atraso de até ~15 h aceito pelo produto | TRANSCRICAO | [09:17] Marcos |
| ADR-004 | `docs/adrs/ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md` | Decisão | HMAC-SHA256 sobre o corpo, secret por endpoint, rotação 24 h | TRANSCRICAO | [09:22] Sofia |
| ADR-004-DEC-01 | `docs/adrs/ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md` | Restrição | TLS obrigatório validado no schema Zod | TRANSCRICAO | [09:23] Sofia |
| ADR-004-ALT-01 | `docs/adrs/ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md` | Alternativa descartada | Secret global | TRANSCRICAO | [09:21] Sofia |
| ADR-004-ALT-02 | `docs/adrs/ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md` | Alternativa descartada | Rotação sem convivência | TRANSCRICAO | [09:21] Sofia |
| ADR-004-ALT-03 | `docs/adrs/ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md` | Alternativa (plausível) | Outro algoritmo de assinatura | TRANSCRICAO | [09:20] Sofia |
| ADR-004-CONS-01 | `docs/adrs/ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md` | Trade-off | Secret precisa ser recuperável, diferente do `passwordHash` | CODIGO | `prisma/schema.prisma` |
| ADR-004-CONS-02 | `docs/adrs/ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md` | Trade-off | Secret não pode ir para logs — ampliar `redact` | CODIGO | `src/shared/logger/index.ts` |
| ADR-005 | `docs/adrs/ADR-005-entrega-at-least-once-com-x-event-id.md` | Decisão | At-least-once com `X-Event-Id` UUID gerado na outbox | TRANSCRICAO | [09:25] Diego |
| ADR-005-DEC-01 | `docs/adrs/ADR-005-entrega-at-least-once-com-x-event-id.md` | Decisão | Documentação destacada no portal | TRANSCRICAO | [09:26] Marcos |
| ADR-005-ALT-01 | `docs/adrs/ADR-005-entrega-at-least-once-com-x-event-id.md` | Alternativa descartada | Exactly-once | TRANSCRICAO | [09:25] Diego |
| ADR-005-ALT-02 | `docs/adrs/ADR-005-entrega-at-least-once-com-x-event-id.md` | Alternativa (plausível) | At-most-once, incompatível com o retry decidido | TRANSCRICAO | [09:15] Diego |
| ADR-005-CONS-01 | `docs/adrs/ADR-005-entrega-at-least-once-com-x-event-id.md` | Trade-off | Responsabilidade de dedup transferida ao cliente | TRANSCRICAO | [09:25] Sofia |
| ADR-006 | `docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md` | Decisão | Reuso máximo: AppError, Pino, error middleware, módulos, Zod | TRANSCRICAO | [09:30] Larissa |
| ADR-006-CTX-01 | `docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md` | Padrão existente | Módulo com controller/service/repository/routes/schemas | CODIGO | `src/modules/orders/order.controller.ts` |
| ADR-006-CTX-02 | `docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md` | Padrão existente | `AppError` com `statusCode` e `errorCode` | CODIGO | `src/shared/errors/app-error.ts` |
| ADR-006-CTX-03 | `docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md` | Padrão existente | Códigos `INVALID_STATUS_TRANSITION`, `INSUFFICIENT_STOCK` | CODIGO | `src/shared/errors/http-errors.ts` |
| ADR-006-CTX-04 | `docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md` | Padrão existente | `requireRole('ADMIN')` já usado em rota de usuários | CODIGO | `src/modules/users/user.routes.ts` |
| ADR-006-DEC-01 | `docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md` | Decisão | Prefixo `WEBHOOK_` nos códigos de erro | TRANSCRICAO | [09:29] Larissa |
| ADR-006-DEC-02 | `docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md` | Decisão | IDs UUID nas novas tabelas | TRANSCRICAO | [09:51] Larissa |
| ADR-006-ALT-01 | `docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md` | Alternativa descartada | Injetar repository inteiro no OrderService | TRANSCRICAO | [09:41] Diego |
| ADR-006-ALT-02 | `docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md` | Alternativa (plausível) | Estrutura própria fora dos padrões | TRANSCRICAO | [09:30] Larissa |
| ADR-006-ALT-03 | `docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md` | Alternativa descartada | Compartilhar instância de PrismaClient | TRANSCRICAO | [09:30] Bruno |
| ADR-006-CONS-01 | `docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md` | Trade-off | Endurecimento de permissões do CRUD adiado | TRANSCRICAO | [09:37] Sofia |
| ADR-007 | `docs/adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md` | Decisão | Payload em snapshot na inserção | TRANSCRICAO | [09:52] Larissa |
| ADR-007-DEC-01 | `docs/adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md` | Decisão | Payload enxuto (campos definidos, sem itens) | TRANSCRICAO | [09:43] Diego |
| ADR-007-DEC-02 | `docs/adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md` | Decisão | Filtro de status na inserção da outbox | TRANSCRICAO | [09:34] Bruno |
| ADR-007-DEC-03 | `docs/adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md` | Restrição | Limite de 64 KB com erro | TRANSCRICAO | [09:24] Diego |
| ADR-007-ALT-01 | `docs/adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md` | Alternativa descartada | Renderizar no envio | TRANSCRICAO | [09:51] Bruno |
| ADR-007-ALT-02 | `docs/adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md` | Alternativa descartada | Filtrar no envio | TRANSCRICAO | [09:34] Diego |
| ADR-007-ALT-03 | `docs/adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md` | Alternativa descartada | Payload completo com itens | TRANSCRICAO | [09:44] Bruno |
| ADR-007-ALT-04 | `docs/adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md` | Alternativa descartada | Truncar payload grande | TRANSCRICAO | [09:23] Sofia |
| FDD-OBJ-01 | `docs/FDD.md` | Objetivo técnico | Latência < 10 s até o primeiro POST | TRANSCRICAO | [09:02] Marcos |
| FDD-OBJ-02 | `docs/FDD.md` | Objetivo técnico | Zero mudanças de status sem evento | TRANSCRICAO | [09:40] Bruno |
| FDD-OBJ-03 | `docs/FDD.md` | Objetivo técnico | Sobreviver a ~14h36min de indisponibilidade | TRANSCRICAO | [09:17] Diego |
| FDD-OBJ-04 | `docs/FDD.md` | Objetivo técnico | Sem mudanças em erro/logger/auth; sem dependência nova | TRANSCRICAO | [09:29] Bruno |
| FDD-EXC-01 | `docs/FDD.md` | Exclusão | Webhooks inbound | TRANSCRICAO | [09:02] Marcos |
| FDD-EXC-02 | `docs/FDD.md` | Exclusão | E-mail de alerta | TRANSCRICAO | [09:37] Larissa |
| FDD-EXC-03 | `docs/FDD.md` | Exclusão | Rate limiting de saída | TRANSCRICAO | [09:39] Larissa |
| FDD-EXC-04 | `docs/FDD.md` | Exclusão | Dashboard visual | TRANSCRICAO | [09:40] Larissa |
| FDD-EXC-05 | `docs/FDD.md` | Exclusão | Arquivamento da outbox | TRANSCRICAO | [09:08] Diego |
| FDD-EXC-06 | `docs/FDD.md` | Exclusão | Múltiplos workers / ordenação global | TRANSCRICAO | [09:13] Diego |
| FDD-EXC-07 | `docs/FDD.md` | Exclusão | Itens do pedido no payload | TRANSCRICAO | [09:43] Diego |
| FDD-EXC-08 | `docs/FDD.md` | Exclusão | `PENDING` nunca gera evento (nenhuma transição leva a ele) | CODIGO | `src/modules/orders/order.status.ts` |
| FDD-EXC-09 | `docs/FDD.md` | Exclusão | Listagem de DLQ via API não discutida | TRANSCRICAO | [09:18] Diego |
| FDD-FLX-01 | `docs/FDD.md` | Fluxo | `publishWebhookEvent` chamado com o `tx` após `orderStatusHistory.create` | TRANSCRICAO | [09:41] Bruno |
| FDD-FLX-02 | `docs/FDD.md` | Fluxo | Seleção de endpoints ativos e filtro por `toStatus` | TRANSCRICAO | [09:34] Bruno |
| FDD-FLX-03 | `docs/FDD.md` | Fluxo | `eventId` UUID + payload snapshot + `PENDING` | TRANSCRICAO | [09:25] Diego |
| FDD-FLX-04 | `docs/FDD.md` | Fluxo | Falha na inserção faz rollback de tudo | TRANSCRICAO | [09:40] Bruno |
| FDD-FLX-05 | `docs/FDD.md` | Fluxo | Boot do worker com PrismaClient próprio e sinais | CODIGO | `src/server.ts` |
| FDD-FLX-06 | `docs/FDD.md` | Fluxo (proposta) | `PROCESSING` volta a `PENDING` no boot (single-worker) | TRANSCRICAO | [09:12] Diego |
| FDD-FLX-07 | `docs/FDD.md` | Fluxo | Polling 2 s, pendentes mais antigos em lote pequeno | TRANSCRICAO | [09:09] Diego |
| FDD-FLX-08 | `docs/FDD.md` | Fluxo | Processamento sequencial preserva ordem por `order_id` | TRANSCRICAO | [09:12] Diego |
| FDD-FLX-09 | `docs/FDD.md` | Fluxo | Endpoint inativo ou sem secret vai para DLQ | TRANSCRICAO | [09:21] Bruno |
| FDD-FLX-10 | `docs/FDD.md` | Fluxo | Checagem de 64 KB no worker, DLQ sem retry | TRANSCRICAO | [09:24] Larissa |
| FDD-FLX-11 | `docs/FDD.md` | Fluxo | Assinatura HMAC-SHA256 e POST com timeout 10 s | TRANSCRICAO | [09:20] Sofia |
| FDD-FLX-12 | `docs/FDD.md` | Fluxo | Registro de cada tentativa em `webhook_deliveries` | TRANSCRICAO | [09:34] Marcos |
| FDD-FLX-13 | `docs/FDD.md` | Fluxo | 2xx = entregue; resto = falha | TRANSCRICAO | [09:42] Diego |
| FDD-FLX-14 | `docs/FDD.md` | Fluxo (proposta) | Erro de banco no ciclo não derruba o loop | TRANSCRICAO | [09:11] Diego |
| FDD-FLX-15 | `docs/FDD.md` | Fluxo | Incremento de `attempts` e `lastError` | TRANSCRICAO | [09:15] Diego |
| FDD-FLX-16 | `docs/FDD.md` | Fluxo | Reagendamento com `RETRY_DELAYS_MS` | TRANSCRICAO | [09:17] Larissa |
| FDD-FLX-17 | `docs/FDD.md` | Fluxo | Após 1 + 5 tentativas, DLQ | TRANSCRICAO | [09:17] Diego |
| FDD-FLX-18 | `docs/FDD.md` | Fluxo | `eventId` e payload imutáveis entre tentativas | TRANSCRICAO | [09:52] Bruno |
| FDD-FLX-19 | `docs/FDD.md` | Fluxo | Outbox `FAILED` + insert em `webhook_dead_letter` | TRANSCRICAO | [09:18] Diego |
| FDD-FLX-20 | `docs/FDD.md` | Fluxo | Replay recoloca na outbox como pendente | TRANSCRICAO | [09:35] Diego |
| FDD-FLX-21 | `docs/FDD.md` | Fluxo | Replay mantém o mesmo `eventId` | TRANSCRICAO | [09:25] Diego |
| FDD-FLX-22 | `docs/FDD.md` | Fluxo | Log de auditoria do replay com usuário | TRANSCRICAO | [09:36] Sofia |
| FDD-FLX-23 | `docs/FDD.md` | Fluxo (proposta) | Nova falha cria nova linha de DLQ (evidência) | TRANSCRICAO | [09:18] Diego |
| FDD-FLX-24 | `docs/FDD.md` | Fluxo | Rotação: secret anterior válida por 24 h | TRANSCRICAO | [09:21] Sofia |
| FDD-FLX-25 | `docs/FDD.md` | Fluxo (proposta) | Assinatura dupla durante o grace period | TRANSCRICAO | [09:21] Sofia |
| FDD-FLX-26 | `docs/FDD.md` | Fluxo (proposta) | Bloqueio de nova rotação durante o grace period | TRANSCRICAO | [09:21] Sofia |
| FDD-CONTRATO-01 | `docs/FDD.md` | Contrato | `POST /api/v1/webhooks` | TRANSCRICAO | [09:31] Marcos |
| FDD-CONTRATO-02 | `docs/FDD.md` | Contrato | `GET /api/v1/customers/:customerId/webhooks` | TRANSCRICAO | [09:33] Bruno |
| FDD-CONTRATO-03 | `docs/FDD.md` | Contrato | `PATCH /api/v1/webhooks/:id` | TRANSCRICAO | [09:33] Bruno |
| FDD-CONTRATO-04 | `docs/FDD.md` | Contrato | `POST /api/v1/webhooks/:id/rotate-secret` | TRANSCRICAO | [09:21] Sofia |
| FDD-CONTRATO-05 | `docs/FDD.md` | Contrato | `DELETE /api/v1/webhooks/:id` (remoção lógica) | TRANSCRICAO | [09:33] Bruno |
| FDD-CONTRATO-06 | `docs/FDD.md` | Contrato | `GET /api/v1/webhooks/:id/deliveries` | TRANSCRICAO | [09:34] Marcos |
| FDD-CONTRATO-07 | `docs/FDD.md` | Contrato | Requisição de saída: payload e headers | TRANSCRICAO | [09:44] Diego |
| FDD-CONTRATO-08 | `docs/FDD.md` | Contrato | `POST /api/v1/admin/webhooks/dead-letter/:id/replay` | TRANSCRICAO | [09:35] Diego |
| FDD-ERR-01 | `docs/FDD.md` | Erro | `WEBHOOK_NOT_FOUND` (404) | TRANSCRICAO | [09:28] Bruno |
| FDD-ERR-02 | `docs/FDD.md` | Erro | `WEBHOOK_INVALID_URL` (400) | TRANSCRICAO | [09:23] Sofia |
| FDD-ERR-03 | `docs/FDD.md` | Erro | `WEBHOOK_CUSTOMER_NOT_FOUND` (404) | CODIGO | `src/modules/orders/order.service.ts` |
| FDD-ERR-04 | `docs/FDD.md` | Erro | `WEBHOOK_SECRET_ROTATION_IN_PROGRESS` (409) | TRANSCRICAO | [09:21] Sofia |
| FDD-ERR-05 | `docs/FDD.md` | Erro | `WEBHOOK_DEAD_LETTER_NOT_FOUND` (404) | TRANSCRICAO | [09:18] Diego |
| FDD-ERR-06 | `docs/FDD.md` | Erro | `WEBHOOK_DEAD_LETTER_ALREADY_REPLAYED` (409) | TRANSCRICAO | [09:35] Diego |
| FDD-ERR-07 | `docs/FDD.md` | Erro | `WEBHOOK_OUTBOX_INSERT_FAILED` (500, rollback) | TRANSCRICAO | [09:40] Bruno |
| FDD-ERR-08 | `docs/FDD.md` | Erro | `WEBHOOK_DELIVERY_TIMEOUT` | TRANSCRICAO | [09:42] Diego |
| FDD-ERR-09 | `docs/FDD.md` | Erro | `WEBHOOK_DELIVERY_FAILED` (não-2xx) | TRANSCRICAO | [09:15] Diego |
| FDD-ERR-10 | `docs/FDD.md` | Erro | `WEBHOOK_DELIVERY_NETWORK_ERROR` | TRANSCRICAO | [09:14] Larissa |
| FDD-ERR-11 | `docs/FDD.md` | Erro | `WEBHOOK_PAYLOAD_TOO_LARGE` | TRANSCRICAO | [09:24] Larissa |
| FDD-ERR-12 | `docs/FDD.md` | Erro | `WEBHOOK_SECRET_REQUIRED` | TRANSCRICAO | [09:28] Bruno |
| FDD-ERR-13 | `docs/FDD.md` | Erro | `WEBHOOK_ENDPOINT_INACTIVE` | TRANSCRICAO | [09:21] Bruno |
| FDD-ERR-14 | `docs/FDD.md` | Erro | `WEBHOOK_MAX_ATTEMPTS_EXCEEDED` | TRANSCRICAO | [09:15] Diego |
| FDD-OBS-01 | `docs/FDD.md` | Observabilidade (log) | Logs de start/stop do worker | CODIGO | `src/server.ts` |
| FDD-OBS-02 | `docs/FDD.md` | Observabilidade (log) | Log por tentativa de entrega | TRANSCRICAO | [09:34] Marcos |
| FDD-OBS-03 | `docs/FDD.md` | Observabilidade (log) | Log de retry agendado | TRANSCRICAO | [09:15] Diego |
| FDD-OBS-04 | `docs/FDD.md` | Observabilidade (log) | Log de envio para DLQ | TRANSCRICAO | [09:18] Diego |
| FDD-OBS-05 | `docs/FDD.md` | Observabilidade (log) | Log de auditoria do replay | TRANSCRICAO | [09:36] Sofia |
| FDD-OBS-06 | `docs/FDD.md` | Observabilidade (log) | Log de rotação sem a secret | TRANSCRICAO | [09:22] Diego |
| FDD-OBS-07 | `docs/FDD.md` | Observabilidade (métrica) | Idade do pendente mais antigo, alerta > 10 s | TRANSCRICAO | [09:02] Marcos |
| FDD-OBS-08 | `docs/FDD.md` | Observabilidade (métrica) | Latência ponta a ponta p95 | TRANSCRICAO | [09:10] Larissa |
| FDD-OBS-09 | `docs/FDD.md` | Observabilidade (métrica) | Taxa de sucesso por webhook | TRANSCRICAO | [09:34] Marcos |
| FDD-OBS-10 | `docs/FDD.md` | Observabilidade (métrica) | Tamanho da DLQ | TRANSCRICAO | [09:18] Diego |
| FDD-OBS-11 | `docs/FDD.md` | Observabilidade (métrica) | Envios por webhook por minuto (insumo para rate limiting) | TRANSCRICAO | [09:39] Diego |
| FDD-OBS-12 | `docs/FDD.md` | Observabilidade (métrica) | Volume da outbox por status | TRANSCRICAO | [09:07] Bruno |
| FDD-OBS-13 | `docs/FDD.md` | Observabilidade (tracing) | Correlação por `orderId` → `eventId` → `webhookId` | TRANSCRICAO | [09:25] Diego |
| FDD-OBS-14 | `docs/FDD.md` | Observabilidade (tracing) | `requestId` do request logger na API | CODIGO | `src/middlewares/request-logger.middleware.ts` |
| FDD-RES-01 | `docs/FDD.md` | Resiliência | Timeout de 10 s | TRANSCRICAO | [09:42] Diego |
| FDD-RES-02 | `docs/FDD.md` | Resiliência | Envio inicial + 5 retentativas | TRANSCRICAO | [09:16] Larissa |
| FDD-RES-03 | `docs/FDD.md` | Resiliência | Backoff 1m/5m/30m/2h/12h | TRANSCRICAO | [09:17] Diego |
| FDD-RES-04 | `docs/FDD.md` | Resiliência | Fallback: DLQ + replay; sem e-mail | TRANSCRICAO | [09:37] Larissa |
| FDD-RES-05 | `docs/FDD.md` | Resiliência | Isolamento: falha do cliente não afeta `changeStatus` | TRANSCRICAO | [09:04] Bruno |
| FDD-RES-06 | `docs/FDD.md` | Resiliência | Crash do worker coberto por at-least-once | TRANSCRICAO | [09:24] Diego |
| FDD-RES-07 | `docs/FDD.md` | Resiliência | Graceful shutdown no padrão da API | CODIGO | `src/server.ts` |
| FDD-RES-08 | `docs/FDD.md` | Resiliência | Erros determinísticos vão direto à DLQ | TRANSCRICAO | [09:23] Sofia |
| FDD-RES-09 | `docs/FDD.md` | Resiliência (proposta) | Banco indisponível: tenta no próximo ciclo | TRANSCRICAO | [09:09] Diego |
| FDD-INT-01 | `docs/FDD.md` | Integração | `changeStatus` chama `publishWebhookEvent(tx, …)` | CODIGO | `src/modules/orders/order.service.ts` |
| FDD-INT-02 | `docs/FDD.md` | Integração | Enum de `events` derivado das transições | CODIGO | `src/modules/orders/order.status.ts` |
| FDD-INT-03 | `docs/FDD.md` | Integração | Erros `Webhook*Error` estendem as classes existentes | CODIGO | `src/shared/errors/http-errors.ts` |
| FDD-INT-04 | `docs/FDD.md` | Integração | Error middleware sem alteração | CODIGO | `src/middlewares/error.middleware.ts` |
| FDD-INT-05 | `docs/FDD.md` | Integração | `authenticate` + `requireRole('ADMIN')` | CODIGO | `src/middlewares/auth.middleware.ts` |
| FDD-INT-06 | `docs/FDD.md` | Integração | `validate` com schemas Zod do módulo | CODIGO | `src/middlewares/validate.middleware.ts` |
| FDD-INT-07 | `docs/FDD.md` | Integração | Logger Pino compartilhado + novos `redactPaths` | CODIGO | `src/shared/logger/index.ts` |
| FDD-INT-08 | `docs/FDD.md` | Integração | Worker usa `createPrismaClient()` | CODIGO | `src/config/database.ts` |
| FDD-INT-09 | `docs/FDD.md` | Integração | Novas variáveis de ambiente `WEBHOOK_*` | CODIGO | `src/config/env.ts` |
| FDD-INT-10 | `docs/FDD.md` | Integração | `src/worker.ts` segue o bootstrap de `server.ts` | TRANSCRICAO | [09:11] Larissa |
| FDD-INT-11 | `docs/FDD.md` | Integração | Montagem dos routers e controllers | CODIGO | `src/routes/index.ts` |
| FDD-INT-12 | `docs/FDD.md` | Integração | Novos modelos Prisma + relação em `Customer` | CODIGO | `prisma/schema.prisma` |
| FDD-INT-13 | `docs/FDD.md` | Integração | Scripts `worker` e `worker:dev` | TRANSCRICAO | [09:11] Larissa |
| FDD-INT-14 | `docs/FDD.md` | Integração | Limpeza das novas tabelas no setup de testes | CODIGO | `tests/setup.ts` |
| FDD-DEP-01 | `docs/FDD.md` | Dependência | Node ≥ 20 para `fetch`, `AbortSignal.timeout`, `crypto` | CODIGO | `package.json` |
| FDD-DEP-02 | `docs/FDD.md` | Dependência | Mesmo MySQL 8 / Prisma, migration aditiva | TRANSCRICAO | [09:11] Diego |
| FDD-DEP-03 | `docs/FDD.md` | Dependência | Reuso de `uuid`, `zod`, `pino` | TRANSCRICAO | [09:29] Bruno |
| FDD-DEP-04 | `docs/FDD.md` | Compatibilidade | Nenhum contrato existente muda | CODIGO | `src/modules/orders/order.routes.ts` |
| FDD-DEP-05 | `docs/FDD.md` | Dependência | Cliente com HTTPS, HMAC e dedup | TRANSCRICAO | [09:26] Marcos |
| FDD-DEP-06 | `docs/FDD.md` | Dependência | Uma única instância do worker | TRANSCRICAO | [09:12] Diego |
| FDD-CA-01 | `docs/FDD.md` | Critério de aceite técnico | Uma linha `PENDING` por endpoint interessado | TRANSCRICAO | [09:06] Diego |
| FDD-CA-02 | `docs/FDD.md` | Critério de aceite técnico | Falha na outbox mantém status, history e estoque | TRANSCRICAO | [09:40] Bruno |
| FDD-CA-03 | `docs/FDD.md` | Critério de aceite técnico | Status fora do filtro não gera linha | TRANSCRICAO | [09:34] Bruno |
| FDD-CA-04 | `docs/FDD.md` | Critério de aceite técnico | http → 400; https → 201 com secret; GET sem secret | TRANSCRICAO | [09:23] Sofia |
| FDD-CA-05 | `docs/FDD.md` | Critério de aceite técnico | Assinatura e headers conferem | TRANSCRICAO | [09:44] Diego |
| FDD-CA-06 | `docs/FDD.md` | Critério de aceite técnico | Retry nos intervalos definidos e DLQ | TRANSCRICAO | [09:17] Diego |
| FDD-CA-07 | `docs/FDD.md` | Critério de aceite técnico | > 64 KB direto para DLQ | TRANSCRICAO | [09:24] Larissa |
| FDD-CA-08 | `docs/FDD.md` | Critério de aceite técnico | Replay: 403 OPERATOR, 202 ADMIN, 409 repetido | TRANSCRICAO | [09:36] Larissa |
| FDD-CA-09 | `docs/FDD.md` | Critério de aceite técnico | Assinatura válida com secret antiga por 24 h | TRANSCRICAO | [09:21] Sofia |
| FDD-CA-10 | `docs/FDD.md` | Critério de aceite técnico | Deliveries limitado a 100 itens | TRANSCRICAO | [09:34] Marcos |
| FDD-CA-11 | `docs/FDD.md` | Critério de aceite técnico | Ordem por `createdAt` sem falhas | TRANSCRICAO | [09:12] Diego |
| FDD-CA-12 | `docs/FDD.md` | Critério de aceite técnico | Nenhum log com secret | TRANSCRICAO | [09:22] Diego |
| FDD-CA-13 | `docs/FDD.md` | Critério de aceite técnico | Lint/testes passam e revisão de segurança feita | TRANSCRICAO | [09:46] Sofia |
| FDD-RISK-01 | `docs/FDD.md` | Risco | Duas instâncias do worker por engano | TRANSCRICAO | [09:13] Diego |
| FDD-RISK-02 | `docs/FDD.md` | Risco | Retry ultrapassado por evento mais novo | TRANSCRICAO | [09:12] Diego |
| FDD-RISK-03 | `docs/FDD.md` | Risco | Crescimento das tabelas | TRANSCRICAO | [09:07] Bruno |
| FDD-RISK-04 | `docs/FDD.md` | Risco | Secret exposta | TRANSCRICAO | [09:22] Diego |
| FDD-RISK-05 | `docs/FDD.md` | Risco | Consulta extra na transação de `changeStatus` | CODIGO | `src/modules/orders/order.service.ts` |
| FDD-RISK-06 | `docs/FDD.md` | Risco | Cliente lento atrasa o lote sequencial | TRANSCRICAO | [09:04] Bruno |
