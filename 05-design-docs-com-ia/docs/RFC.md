# RFC — Sistema de Webhooks de Notificação de Pedidos

| Campo | Valor |
| --- | --- |
| **ID** | RFC-001 |
| **Autor** | Matheus Bombonato (a partir da reunião técnica conduzida por Larissa, Tech Lead) |
| **Status** | Em revisão |
| **Data** | 2026-11-09 |
| **Revisores** | Larissa (Tech Lead) · Marcos (Product Manager) · Bruno (Eng. Pleno, Pedidos) · Diego (Eng. Sênior, Plataforma) · Sofia (Eng. de Segurança) |
| **Documentos relacionados** | [PRD](PRD.md) · [FDD](FDD.md) · [ADRs](adrs/README.md) · [Tracker](TRACKER.md) |

> Este RFC propõe a abordagem e abre os pontos não resolvidos para revisão. As decisões fechadas estão nos ADRs; o detalhamento de implementação (schema, contratos, erros, fluxos passo a passo) está no FDD.

## Resumo executivo (TL;DR)

Propomos notificar clientes B2B, via **webhooks outbound**, a cada mudança de status de pedido. O evento é gravado numa **tabela outbox no MySQL existente, na mesma transação** do `changeStatus`; um **worker em processo separado** lê a outbox **a cada 2 s** e faz o POST HTTPS assinado com **HMAC-SHA256 (secret por endpoint)**. Falhas seguem **backoff exponencial 1m/5m/30m/2h/12h** e, esgotadas, vão para uma **DLQ** com replay manual por ADMIN. A entrega é **at-least-once**, com **`X-Event-Id`** para deduplicação no cliente. Tudo dentro dos padrões atuais do projeto, **sem infraestrutura nova**. Estimativa: **3 sprints**, incluindo revisão de segurança.

## Contexto e problema

- Três clientes B2B (Atlas Comercial, MaxDistribuição e Nova Cargo) pediram formalmente notificação em tempo real de mudança de status. Hoje eles fazem polling em `GET /orders`, o que deixa a integração lenta e cara; a Atlas sinalizou possível migração para concorrente se não houver entrega até o fim do trimestre (`[09:00] Marcos`).
- Para os clientes, "tempo real" é **qualquer coisa abaixo de 10 s** (`[09:02] Marcos`).
- O OMS não possui hoje nenhum mecanismo de eventos, filas ou notificação externa. A mudança de status vive em `OrderService.changeStatus` (`src/modules/orders/order.service.ts`), numa transação que já atualiza `orders`, insere em `order_status_history` e movimenta estoque (`[09:04] Bruno`).
- Restrição central: **nenhuma mudança de status pode acontecer sem que o evento correspondente seja registrado**, e uma falha do cliente não pode desfazer a mudança de status (`[09:04] Bruno`, `[09:40] Bruno`).

## Proposta técnica

Visão em quatro blocos (detalhes no [FDD](FDD.md)):

```
 API (src/server.ts)                          Worker (src/worker.ts)                 Cliente B2B
 ┌───────────────────────────────┐           ┌────────────────────────────┐        ┌───────────┐
 │ PATCH /orders/:id/status      │           │ loop a cada 2 s            │ HTTPS  │ endpoint  │
 │  └ changeStatus ($transaction)│  MySQL    │  lê PENDING mais antigos   │ ─────► │ https://… │
 │     ├ update orders           │ ┌──────┐  │  assina HMAC-SHA256        │ ◄───── │ 2xx / erro│
 │     ├ insert status_history   │►│outbox│─►│  POST (timeout 10 s)       │        └───────────┘
 │     └ publishWebhookEvent(tx) │ └──────┘  │  sucesso → DELIVERED       │
 │ CRUD /webhooks, deliveries    │ ┌──────┐  │  falha → retry c/ backoff  │
 │ POST /admin/.../replay (ADMIN)│◄│ DLQ  │◄─│  esgotou → dead letter     │
 └───────────────────────────────┘ └──────┘  └────────────────────────────┘
```

1. `RFC-PROP-01` **Captura transacional (outbox).** Dentro da transação de `changeStatus`, uma função pura (detalhada no FDD) grava um evento por webhook ativo do customer interessado naquele status. O payload é um snapshot enxuto do pedido. Se a gravação falhar, a mudança de status inteira faz rollback. → [ADR-001](adrs/ADR-001-outbox-transacional-no-mysql.md), [ADR-007](adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md)
2. `RFC-PROP-02` **Despacho assíncrono (worker).** Processo Node separado, mesma base e stack, com `PrismaClient` próprio, fazendo polling de 2 s. Roda como instância única, o que garante ordenação apenas por `order_id`. → [ADR-002](adrs/ADR-002-worker-separado-com-polling.md)
3. `RFC-PROP-03` **Confiabilidade.** Timeout de 10 s, 5 retentativas com backoff exponencial, DLQ em tabela própria e replay manual por ADMIN. Entrega at-least-once com `X-Event-Id` estável. → [ADR-003](adrs/ADR-003-retry-com-backoff-exponencial-e-dlq.md), [ADR-005](adrs/ADR-005-entrega-at-least-once-com-x-event-id.md)
4. `RFC-PROP-04` **Segurança.** Só URLs `https`; HMAC-SHA256 sobre o corpo, secret única por endpoint gerada pela plataforma, rotação com convivência de 24 h; limite de 64 KB por payload. → [ADR-004](adrs/ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md)
5. `RFC-PROP-05` **Superfície de API e padrões.** Novo módulo `src/modules/webhooks` (a criar) no padrão controller/service/repository/routes/schemas, erros `WEBHOOK_*` sobre `AppError`, logger Pino, `requireRole('ADMIN')` no replay. CRUD de configuração aberto a qualquer usuário autenticado; `customer_id` informado na requisição, não extraído do JWT. → [ADR-006](adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md)

## Alternativas consideradas

| ID | Alternativa | Trade-off que motivou o descarte | Fonte |
| --- | --- | --- | --- |
| RFC-ALT-01 | **Disparo HTTP síncrono dentro de `changeStatus`** | Acopla a disponibilidade do cliente à transação de pedidos: cliente lento trava mudanças de status de outros pedidos e cliente fora do ar forçaria rollback da mudança de status. | `[09:04] Bruno`, `[09:06] Diego` |
| RFC-ALT-02 | **Redis Streams / fila externa** | Exige subir e operar Redis Cluster; para um time pequeno é overengineering frente ao MySQL já existente. | `[09:07] Larissa`, `[09:07] Diego` |
| RFC-ALT-03 | **Trigger de banco para acordar o worker** | Seria mais reativo que polling, mas o MySQL não tem `LISTEN/NOTIFY`; a trigger não notifica processo externo, e qualquer improviso (arquivo, endpoint) é frágil. Polling de 2 s já atende os 10 s. | `[09:09] Bruno`, `[09:09] Diego` |
| RFC-ALT-04 | **Retry indefinido** ou **apenas 3 tentativas** | Indefinido deixa eventos pendurados para sempre; 3 tentativas cobrem só ~30 min e não sobrevivem a uma manutenção de 2 h. | `[09:15] Diego`, `[09:16] Bruno`, `[09:16] Diego` |
| RFC-ALT-05 | **Exactly-once** | Exigiria coordenação dos dois lados e muito mais complexidade; at-least-once + `event_id` é o padrão de mercado (Stripe, GitHub). | `[09:25] Diego` |
| RFC-ALT-06 | **Secret global da plataforma** | Simples de operar, mas um vazamento comprometeria todos os clientes. | `[09:21] Sofia` |

## Questões em aberto

| ID | Questão | Estado na reunião | Proposta deste RFC | Fonte |
| --- | --- | --- | --- | --- |
| RFC-QA-01 | **Rate limiting de saída** por cliente (ex.: 50 mudanças de status em 1 min viram 50 chamadas). | Fora do escopo; "observar e decidir depois". | Medir chamadas por webhook/minuto nos logs do worker (FDD §8) e reabrir se aparecer reclamação. | `[09:38] Diego`, `[09:39] Larissa` |
| RFC-QA-02 | **Notificação por e-mail** ao cliente quando o webhook falha repetidamente. | Adiado para próxima fase, após medir impacto. | Nesta fase, a única visibilidade é `GET /webhooks/:id/deliveries` e a DLQ. | `[09:37] Larissa`, `[09:38] Marcos` |
| RFC-QA-03 | **Escala para múltiplos workers** (particionar por `order_id` ou lock pessimista). | "Problema do futuro"; documentado como limitação. | Manter single-worker; o desenho da outbox não impede particionamento posterior. | `[09:13] Diego`, `[09:13] Larissa` |
| RFC-QA-04 | **Endurecer permissões do CRUD** de webhooks (hoje qualquer role autenticada). | "Mais pra frente a gente pode endurecer." | Sem mudança na v1. | `[09:37] Sofia` |
| RFC-QA-05 | **Arquivamento** das linhas entregues da outbox (~30 dias). | Fora do escopo desta feature. | Sem job de limpeza na v1; acompanhar volume da tabela. | `[09:08] Diego` |
| RFC-QA-06 | **Ordenação x retry.** Com single-worker a ordem por `order_id` vale para a primeira tentativa, mas um evento em backoff pode ser ultrapassado por um evento mais novo do mesmo pedido. A reunião não tratou essa interação. | Não discutido. | V1 entrega na ordem de `created_at` sem bloquear eventos mais novos; o cliente usa `timestamp` do payload para descartar estado antigo. Revisores devem confirmar se isso é aceitável. | `[09:12] Diego`, `[09:14] Marcos` |
| RFC-QA-07 | **Contagem de tentativas**: "5 tentativas" com 5 intervalos (1m…12h, "quase 15 horas") só fecha como 1 envio inicial + 5 retentativas. | Ambíguo. | Adotar 1 + 5 (ADR-003); Diego confirma na sessão de revisão. | `[09:15] Diego`, `[09:17] Diego`, `[09:17] Larissa` |
| RFC-QA-08 | **Armazenamento da secret e assinatura durante o grace period** (em claro x cifrada; como sinalizar as duas secrets válidas nas 24 h). | Não detalhado; Sofia quer revisar HMAC e geração de secret com calma. | FDD traz uma proposta marcada como pendente de validação na revisão de segurança. | `[09:21] Sofia`, `[09:46] Sofia` |
| RFC-QA-09 | **`customer_id` no body ou no path.** | Definido que não vem do JWT, mas o local ficou em aberto. | Proposta: no body do cadastro e no path da listagem; o contrato fica no FDD. | `[09:32] Larissa` |

## Impacto e riscos

**Impacto no sistema existente**

- `changeStatus` ganha uma etapa transacional extra; nenhum contrato atual de `/orders` muda.
- Novas tabelas no `prisma/schema.prisma` (configuração, outbox, histórico de entregas, dead letter) e uma migration.
- Novo processo para operar (`npm run worker`) com o mesmo `DATABASE_URL`.
- Novo módulo e rotas sob `/api/v1`; padrões de erro, log e auth inalterados.

**Riscos principais**

| ID | Risco | Prob. | Impacto | Mitigação |
| --- | --- | --- | --- | --- |
| RFC-RISK-01 | Falha na inserção da outbox bloquear mudanças de status (rollback). | Baixa | Alto | É o comportamento desejado (consistência, `[09:40] Bruno`); cobrir com teste de integração de rollback (FDD-CA-02). |
| RFC-RISK-02 | Worker parado ⇒ eventos acumulam e a latência estoura os 10 s. | Média | Alto | Processo separado da API; alerta sobre idade do evento pendente mais antigo (FDD §8). |
| RFC-RISK-03 | Clientes não deduplicam e processam eventos repetidos. | Média | Médio | `X-Event-Id` estável e documentação destacada no portal (`[09:26] Marcos`). |
| RFC-RISK-04 | Vazamento de secret de um cliente. | Média | Médio | Secret por endpoint, rotação com 24 h, `redact` no logger, revisão da Sofia. |
| RFC-RISK-05 | Prazo: Atlas quer até fim de novembro; estimativa de 3 sprints com 2 dias de revisão de segurança. | Média | Alto | Marcos confirma prazo com a Atlas; revisão de segurança agendada desde já (`[09:46] Sofia`, `[09:47] Marcos`). |

## Decisões relacionadas

- [ADR-001 — Outbox transacional no MySQL existente](adrs/ADR-001-outbox-transacional-no-mysql.md)
- [ADR-002 — Worker em processo separado com polling de 2 segundos](adrs/ADR-002-worker-separado-com-polling.md)
- [ADR-003 — Retry com backoff exponencial e DLQ em tabela separada](adrs/ADR-003-retry-com-backoff-exponencial-e-dlq.md)
- [ADR-004 — HMAC-SHA256 com secret por endpoint e rotação com grace period de 24 h](adrs/ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md)
- [ADR-005 — Entrega at-least-once com deduplicação por `X-Event-Id`](adrs/ADR-005-entrega-at-least-once-com-x-event-id.md)
- [ADR-006 — Reuso máximo dos padrões existentes do projeto](adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md)
- [ADR-007 — Payload enxuto em snapshot e filtro de eventos na inserção](adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md)

## Próximos passos

1. Sessão de revisão deste RFC com Bruno e Diego antes de começar a codar (`[09:50] Larissa`).
2. Fechar RFC-QA-06, RFC-QA-07 e RFC-QA-08 nessa sessão / na revisão de segurança.
3. Agendar os 2 dias úteis de revisão de segurança da Sofia antes do deploy (`[09:46] Sofia`).
