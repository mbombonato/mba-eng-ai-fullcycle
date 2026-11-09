# ADR-003 — Retry com backoff exponencial (1m/5m/30m/2h/12h) e DLQ em tabela separada

- **Status:** Aceito
- **Data da decisão:** reunião técnica de webhooks (decisões fechadas em `[09:17] Larissa` e `[09:19] Larissa`)
- **Decisores:** Larissa (Tech Lead), Diego (Plataforma), Bruno (Pedidos), Marcos (Produto), Sofia (Segurança)
- **Relacionados:** [RFC](../RFC.md) · [FDD §5.3 e §5.4](../FDD.md#53-fluxo-3--retry-com-backoff) · [ADR-005](ADR-005-entrega-at-least-once-com-x-event-id.md)

## Contexto

O endpoint do cliente pode estar lento ou fora do ar. Já houve cliente com indisponibilidade de duas horas em manutenção planejada (`[09:16] Diego`). Ao mesmo tempo, um evento não pode ficar pendurado para sempre se o cliente sumiu (`[09:15] Diego`). Eventos que esgotarem as tentativas precisam ficar disponíveis para depuração e reprocessamento (`[09:18] Diego`).

## Decisão

1. **Backoff exponencial com teto de tentativas** (`[09:15] Diego`). Após a primeira tentativa falhar, novas tentativas são agendadas com atrasos de **1 min, 5 min, 30 min, 2 h e 12 h** (`[09:17] Diego`, `[09:17] Larissa`) — janela total de ~14h36min entre a primeira falha e a última tentativa ("quase 15 horas", `[09:17] Diego`).
2. **Teto de 5 tentativas** (`[09:16] Larissa`). Interpretação adotada: os 5 atrasos acima correspondem a 5 **retentativas** após o envio inicial, pois só assim a janela de "quase 15 horas" citada fecha. Essa leitura está registrada como questão de confirmação no [RFC](../RFC.md#questões-em-aberto).
3. **Timeout de 10 s por chamada HTTP**; não responder nesse prazo conta como falha e agenda retry (`[09:42] Diego`).
4. **DLQ em tabela separada `webhook_dead_letter`**, com payload, motivo da falha e timestamp (`[09:18] Diego`), em vez de apenas marcar a linha da outbox.
5. **Reprocessamento manual** via `POST /admin/webhooks/dead-letter/:id/replay`, que recoloca o evento na outbox como pendente (`[09:18] Diego`). O endpoint exige role `ADMIN` e registra em log quem executou o replay (`[09:36] Sofia`, `[09:36] Larissa`).

## Alternativas Consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| **Retry indefinido com backoff** | Evento fica pendurado para sempre se o cliente desapareceu (`[09:15] Diego`). |
| **Apenas 3 tentativas** (proposta de `[09:16] Bruno`) | Cobriria só ~30 minutos; uma indisponibilidade de manhã ou uma manutenção de 2 h mataria o evento (`[09:16] Diego`). |
| **Marcar como `failed` na própria outbox (sem tabela de DLQ)** | Levantada por `[09:17] Larissa`; preterida porque a tabela separada mantém a leitura da outbox principal limpa e funciona como evidência para debug e replay (`[09:18] Diego`). |

## Consequências

**Positivas**

- Cobre indisponibilidades longas (até ~15 h), inclusive manutenções planejadas.
- Eventos com falha permanente não se perdem: ficam na DLQ com o motivo, prontos para replay.
- Outbox principal fica enxuta, o que mantém a consulta do worker rápida.

**Negativas / trade-offs**

- Um evento pode chegar com até ~15 h de atraso; aceito pelo produto: "se um cliente meu cair por 15 horas, ele já tá com problema sério dele" (`[09:17] Marcos`).
- Replay é manual e depende de um ADMIN; não há reprocessamento automático nem aviso ao cliente (e-mail adiado, `[09:37] Larissa`).
- Retentativas atrasadas convivem com eventos mais novos do mesmo pedido, o que tensiona a garantia de ordenação de [ADR-002](ADR-002-worker-separado-com-polling.md) — ver questão em aberto no [RFC](../RFC.md#questões-em-aberto).
