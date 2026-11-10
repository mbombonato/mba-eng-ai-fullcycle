# ADR-006 — Reuso máximo dos padrões existentes do projeto

- **Data da decisão:** reunião técnica de webhooks (decisão fechada em `[09:30] Larissa`)
- **Decisores:** Larissa (Tech Lead), Bruno (Pedidos), Diego (Plataforma), Sofia (Segurança)
- **Relacionados:** [RFC](../RFC.md) · [FDD §10 — Integração com o sistema existente](../FDD.md#10-integração-com-o-sistema-existente) · [ADR-002](ADR-002-worker-separado-com-polling.md)

## Status

Aceito

## Contexto

O OMS já tem convenções consolidadas, verificáveis no código:

| Padrão | Onde está no código |
| --- | --- |
| Um módulo por domínio com `controller`, `service`, `repository`, `routes` e `schemas` | `src/modules/orders/`, `src/modules/customers/`, `src/modules/products/`, `src/modules/users/` |
| Classe base de erro com `statusCode` + `errorCode` | `src/shared/errors/app-error.ts` (`AppError`) |
| Erros de domínio com código em `UPPER_SNAKE_CASE` | `src/shared/errors/http-errors.ts` (`InvalidStatusTransitionError` → `INVALID_STATUS_TRANSITION`, `InsufficientStockError` → `INSUFFICIENT_STOCK`) |
| Tratamento centralizado de `AppError`, `ZodError` e erros do Prisma | `src/middlewares/error.middleware.ts` |
| Validação de body/query/params com Zod | `src/middlewares/validate.middleware.ts` |
| Autenticação JWT e autorização por role | `src/middlewares/auth.middleware.ts` (`authenticate`, `requireRole`) |
| Logger estruturado Pino com `redact` | `src/shared/logger/index.ts` |
| Chaves primárias UUID (`@default(uuid()) @db.Char(36)`) | `prisma/schema.prisma` |

A reunião discutiu se o módulo de webhooks deveria trazer bibliotecas ou estruturas próprias.

## Decisão

O módulo de webhooks **segue exatamente os padrões existentes** e não introduz infraestrutura transversal nova (`[09:30] Larissa`):

1. **Estrutura modular:** nova pasta `src/modules/webhooks/` com `webhook.controller.ts`, `webhook.service.ts`, `webhook.repository.ts`, `webhook.routes.ts`, `webhook.schemas.ts`, mais `webhook.processor.ts` para a lógica do worker (`[09:27] Bruno`, `[09:28] Bruno`).
2. **Erros:** novas classes estendem `AppError` (ou suas subclasses `NotFoundError`/`ConflictError`/`BadRequestError`), com códigos prefixados por **`WEBHOOK_`** — por exemplo `WEBHOOK_NOT_FOUND`, `WEBHOOK_INVALID_URL`, `WEBHOOK_SECRET_REQUIRED` (`[09:28] Bruno`, `[09:29] Larissa`).
3. **Error middleware:** nenhuma alteração; `errorMiddleware` já serializa qualquer `AppError` como `{ error: { code, message, details } }` (`[09:29] Bruno`).
4. **Logger:** Pino, o mesmo `logger` de `src/shared/logger/index.ts`, em API e worker; "não vamos botar nada novo" (`[09:29] Bruno`).
5. **Autorização:** o replay da DLQ reaproveita `requireRole('ADMIN')`, como já feito em `src/modules/users/user.routes.ts` (`[09:36] Larissa`).
6. **Integração com pedidos:** em vez de injetar um repository inteiro no `OrderService`, uma função pura `publishWebhookEvent(tx, order, fromStatus, toStatus)` recebe o `Prisma.TransactionClient` da transação corrente (`[09:41] Bruno`, `[09:41] Diego`).
7. **Identificadores UUID** em todas as novas tabelas (`[09:51] Larissa`).

## Alternativas Consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| **Injetar um `WebhookRepository` no construtor de `OrderService`** | Exigiria alterar a composição em `src/app.ts` e acoplar o serviço de pedidos ao módulo de webhooks; a função pura que recebe o `tx` resolve com menos acoplamento (`[09:41] Diego`). |
| **Estrutura própria para o módulo (fora de `src/modules`, outro logger, erros sem padrão)** (plausível) | Fragmenta a base, duplica tratamento de erro e observabilidade e aumenta o custo de revisão; contraria a decisão explícita de reuso (`[09:30] Larissa`). |
| **Compartilhar a instância de `PrismaClient` entre API e worker** | Impossível: são processos Node diferentes; o worker usa a mesma `DATABASE_URL` com instância própria (`[09:30] Bruno`). |

## Consequências

**Positivas**

- Curva de aprendizado mínima: quem conhece `orders` consegue ler `webhooks`.
- Erros do módulo chegam ao cliente HTTP no mesmo formato de todos os outros, sem mexer em `src/middlewares/error.middleware.ts`.
- Nenhuma dependência nova no `package.json` além do script `worker`.

**Negativas / trade-offs**

- O módulo herda as limitações do padrão atual (por exemplo, roles restritos a `ADMIN`/`OPERATOR`, sem papel específico de "cliente"), o que limita o endurecimento de permissões no CRUD — adiado (`[09:37] Sofia`).
- Sem bibliotecas novas, métricas e tracing precisam ser derivados de logs Pino estruturados e consultas ao banco, em vez de uma ferramenta dedicada (ver [FDD §8](../FDD.md#8-observabilidade)).
