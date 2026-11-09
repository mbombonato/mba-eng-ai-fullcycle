# ADR-007 — Payload enxuto renderizado como snapshot e filtro de eventos na inserção da outbox

- **Status:** Aceito
- **Data da decisão:** reunião técnica de webhooks (decisões fechadas em `[09:34] Bruno`, `[09:44] Bruno` e `[09:52] Bruno`)
- **Decisores:** Larissa (Tech Lead), Diego (Plataforma), Bruno (Pedidos), Marcos (Produto)
- **Relacionados:** [RFC](../RFC.md) · [FDD §5.1 e §6.8](../FDD.md#51-fluxo-1--criação-do-evento-na-outbox) · [ADR-001](ADR-001-outbox-transacional-no-mysql.md)

## Contexto

Ao gravar o evento na outbox ([ADR-001](ADR-001-outbox-transacional-no-mysql.md)) é preciso definir três coisas: **o que** gravar (payload pronto ou só referência ao pedido), **quanto** do pedido enviar, e **quando** aplicar o filtro de status que cada webhook quer ouvir (`[09:33] Marcos`). O pedido pode continuar mudando depois do evento, e a tabela de outbox não deve crescer à toa.

## Decisão

1. **Snapshot na inserção:** o payload é renderizado e gravado já na inserção da outbox, refletindo o estado do pedido no momento da mudança de status (`[09:52] Larissa`, `[09:52] Diego`, `[09:52] Bruno`).
2. **Payload enxuto:** JSON com `event_id`, `event_type` (`"order.status_changed"`), `timestamp` ISO 8601, `order_id`, `order_number`, `from_status`, `to_status`, `customer_id` e campos básicos do pedido como `total_cents`. **Itens do pedido não são enviados**; quem precisar de detalhes consulta `GET /orders/:id` (`[09:43] Diego`, `[09:44] Bruno`).
3. **Filtro na inserção:** cada webhook declara a lista de status que quer receber; o filtro é aplicado no momento de inserir na outbox. Se nenhum webhook ativo do customer quer aquele status, nada é inserido (`[09:33] Marcos`, `[09:34] Bruno`, `[09:34] Diego`).
4. **Limite de 64 KB** por payload; acima disso o evento não é enviado e é tratado como erro, nunca truncado (`[09:23] Sofia`, `[09:24] Diego`, `[09:24] Larissa`).

## Alternativas Consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| **Gravar só `order_id` e renderizar no envio** | Se o pedido mudar depois, o evento deixaria de refletir o estado do momento da transição, gerando "caso esquisito" (`[09:52] Larissa`). |
| **Filtrar no momento do envio** (levantada por `[09:34] Diego`) | Inseriria linhas que nunca seriam enviadas; filtrar na inserção economiza linhas na tabela (`[09:34] Bruno`). |
| **Payload completo com itens** | Infla o payload sem necessidade; o cliente pode buscar detalhes sob demanda (`[09:43] Diego`). |
| **Truncar payloads acima do limite** | Payload tão grande indica erro; a decisão foi recusar, não truncar (`[09:23] Sofia`). |

## Consequências

**Positivas**

- Evento imutável e fiel ao momento da transição; retry e replay enviam exatamente o mesmo conteúdo, coerente com a deduplicação por `event_id` ([ADR-005](ADR-005-entrega-at-least-once-com-x-event-id.md)).
- O worker não precisa consultar `orders` para enviar; só lê a outbox.
- Outbox menor, pois eventos sem interessado não geram linhas.

**Negativas / trade-offs**

- Mais trabalho dentro da transação de `changeStatus` (consultar webhooks do customer e serializar o payload).
- Alterar o filtro de um webhook só afeta eventos futuros; eventos já inseridos seguem seu curso.
- Clientes que precisam dos itens farão uma chamada adicional a `GET /orders/:id`.
