# ADR-001 — Outbox transacional no MySQL existente

- **Status:** Aceito
- **Data da decisão:** reunião técnica de webhooks (decisão fechada em `[09:08] Larissa`)
- **Decisores:** Larissa (Tech Lead), Diego (Plataforma), Bruno (Pedidos)
- **Relacionados:** [RFC](../RFC.md) · [FDD §5.1](../FDD.md#51-fluxo-1--criação-do-evento-na-outbox) · [ADR-002](ADR-002-worker-separado-com-polling.md) · [ADR-007](ADR-007-snapshot-do-payload-e-filtro-na-insercao.md)

## Contexto

Clientes B2B precisam ser avisados quando o status de um pedido muda. A mudança de status acontece em `OrderService.changeStatus` (`src/modules/orders/order.service.ts`), que já executa, dentro de um único `prisma.$transaction`, a validação da máquina de estados (`src/modules/orders/order.status.ts`), o débito/reposição de estoque, o `UPDATE` em `orders` e o `INSERT` em `order_status_history`.

Foram levantadas três restrições na reunião:

1. A transação já é "pesada"; incluir uma chamada HTTP dentro dela faria um cliente lento travar a mudança de status de outros pedidos (`[09:04] Bruno`).
2. Se o cliente estiver fora do ar, não é aceitável fazer rollback da mudança de status (`[09:04] Bruno`).
3. Não pode existir o caso de "status mudou e evento não saiu" (`[09:40] Bruno`, `[09:41] Diego`).

O time é pequeno e não quer operar infraestrutura nova (`[09:07] Diego`).

## Decisão

Adotar o **padrão Transactional Outbox no MySQL que a aplicação já usa**:

- Uma nova tabela `webhook_outbox` recebe uma linha por evento **na mesma transação** de `changeStatus` (`[09:06] Diego`). Commit da transação ⇒ evento registrado; rollback ⇒ evento descartado junto.
- Falha ao inserir na outbox **aborta a transação inteira** (`[09:40] Bruno`).
- A tabela tem índices em `status` (pendente, processando, falhou, entregue) e `created_at`, e é lida em lotes pequenos (`[09:08] Diego`).
- Chaves primárias em UUID, seguindo o restante do schema (`[09:51] Larissa`).
- O despacho HTTP é feito fora da transação, por um worker ([ADR-002](ADR-002-worker-separado-com-polling.md)).

## Alternativas Consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| **Disparo síncrono dentro de `changeStatus`** | Acopla a latência do cliente à transação; um cliente lento bloqueia a mudança de status de outros pedidos e uma indisponibilidade exigiria rollback da mudança de status, o que é inaceitável (`[09:04] Bruno`, `[09:06] Diego`). |
| **Redis Streams / fila dedicada** | Exige subir e operar infraestrutura nova (Redis Cluster); para um time pequeno é overengineering (`[09:07] Larissa`, `[09:07] Diego`). Além disso, publicar numa fila externa fora da transação MySQL reintroduz o problema de dual-write. |

## Consequências

**Positivas**

- Atomicidade entre mudança de status e registro do evento, sem coordenação distribuída (`[09:06] Diego`).
- Zero infraestrutura nova: mesmo MySQL, mesmo Prisma, mesma stack.
- A outbox serve como trilha de auditoria do que deveria ter sido enviado.

**Negativas / trade-offs**

- A transação de `changeStatus` ganha mais um `INSERT` por webhook interessado, aumentando levemente seu custo — aceito em troca da garantia de consistência.
- O MySQL passa a acumular linhas de eventos; o arquivamento das linhas entregues (~30 dias) ficou **fora do escopo** desta feature (`[09:08] Diego`).
- Latência mínima passa a depender do intervalo de leitura do worker (ver [ADR-002](ADR-002-worker-separado-com-polling.md)).
