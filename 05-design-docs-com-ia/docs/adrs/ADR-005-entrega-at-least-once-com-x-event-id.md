# ADR-005 — Garantia de entrega at-least-once com deduplicação por `X-Event-Id`

- **Data da decisão:** reunião técnica de webhooks (decisão fechada em `[09:26] Larissa`)
- **Decisores:** Diego (Plataforma), Larissa (Tech Lead), Sofia (Segurança), Marcos (Produto)
- **Relacionados:** [RFC](../RFC.md) · [FDD §6.8](../FDD.md#68-contrato-de-saída-requisição-enviada-ao-cliente) · [ADR-001](ADR-001-outbox-transacional-no-mysql.md) · [ADR-003](ADR-003-retry-com-backoff-exponencial-e-dlq.md)

## Status

Aceito

## Contexto

Com outbox + worker + retry ([ADR-001](ADR-001-outbox-transacional-no-mysql.md), [ADR-003](ADR-003-retry-com-backoff-exponencial-e-dlq.md)), há janelas em que o cliente recebe e processa o evento, mas a confirmação não chega até nós (timeout, queda de rede, worker reiniciando após enviar e antes de marcar como entregue). Nesses casos o evento será reenviado. Replays manuais da DLQ também reenviam eventos.

## Decisão

1. A plataforma garante **entrega at-least-once**: o cliente pode receber o mesmo evento mais de uma vez e precisa estar preparado (`[09:24] Diego`).
2. Cada evento recebe um **UUID gerado no momento da inserção na outbox**, único por evento, enviado no header **`X-Event-Id`** e no campo `event_id` do payload (`[09:25] Diego`, `[09:43] Diego`).
3. O mesmo `event_id` é mantido em todas as retentativas e em replays da DLQ, para que o cliente consiga **deduplicar do lado dele** (`[09:25] Diego`).
4. O comportamento será documentado com destaque no portal do desenvolvedor (`[09:26] Marcos`).

## Alternativas Consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| **Exactly-once** | Exigiria coordenação dos dois lados (nós e cliente) e é muito mais complexo; at-least-once com `event_id` resolve a grande maioria dos casos e é o que Stripe e GitHub praticam (`[09:25] Diego`). |
| **At-most-once (sem retry)** | Implícita e incompatível com a política de retry/DLQ já decidida em [ADR-003](ADR-003-retry-com-backoff-exponencial-e-dlq.md): perderia eventos em qualquer indisponibilidade do cliente. |

## Consequências

**Positivas**

- Nenhum evento é perdido silenciosamente; o modelo é simples de implementar com outbox.
- Alinhado ao padrão de mercado, reduzindo atrito de integração para clientes que já consomem webhooks de outras plataformas.

**Negativas / trade-offs**

- **Transfere responsabilidade ao cliente**, que precisa implementar deduplicação (`[09:25] Sofia`). Mitigação: documentação destacada no portal (`[09:26] Marcos`).
- Clientes que não deduplicarem podem processar o mesmo evento em duplicidade.
