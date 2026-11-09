# Architectural Decision Records

Este diretório armazena os ADRs (Architectural Decision Records) do projeto.
Cada decisão arquitetural relevante é registrada em um arquivo individual, no formato
`ADR-NNN-titulo-em-kebab-case.md` (variante MADR: Status, Contexto, Decisão,
Alternativas Consideradas, Consequências).

## Índice — Sistema de Webhooks de Notificação de Pedidos

| ADR | Decisão | Status |
| --- | --- | --- |
| [ADR-001](ADR-001-outbox-transacional-no-mysql.md) | Outbox transacional no MySQL existente | Aceito |
| [ADR-002](ADR-002-worker-separado-com-polling.md) | Worker em processo separado com polling de 2 s | Aceito |
| [ADR-003](ADR-003-retry-com-backoff-exponencial-e-dlq.md) | Retry com backoff exponencial e DLQ em tabela separada | Aceito |
| [ADR-004](ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md) | HMAC-SHA256 com secret por endpoint e rotação com grace period de 24 h | Aceito |
| [ADR-005](ADR-005-entrega-at-least-once-com-x-event-id.md) | Entrega at-least-once com deduplicação por `X-Event-Id` | Aceito |
| [ADR-006](ADR-006-reuso-dos-padroes-existentes-do-projeto.md) | Reuso máximo dos padrões existentes do projeto | Aceito |
| [ADR-007](ADR-007-snapshot-do-payload-e-filtro-na-insercao.md) | Payload enxuto em snapshot e filtro de eventos na inserção | Aceito |
