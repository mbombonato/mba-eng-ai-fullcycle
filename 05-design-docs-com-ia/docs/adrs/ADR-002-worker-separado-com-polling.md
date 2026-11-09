# ADR-002 — Worker em processo separado com polling de 2 segundos

- **Status:** Aceito
- **Data da decisão:** reunião técnica de webhooks (decisão fechada em `[09:10] Larissa`)
- **Decisores:** Larissa (Tech Lead), Diego (Plataforma), Bruno (Pedidos), Marcos (Produto)
- **Relacionados:** [RFC](../RFC.md) · [FDD §5.2](../FDD.md#52-fluxo-2--processamento-pelo-worker) · [ADR-001](ADR-001-outbox-transacional-no-mysql.md)

## Contexto

Com a outbox ([ADR-001](ADR-001-outbox-transacional-no-mysql.md)), alguém precisa ler os eventos pendentes e fazer as chamadas HTTP. Os clientes consideram "tempo real" qualquer coisa abaixo de 10 segundos (`[09:02] Marcos`). O MySQL não tem um mecanismo nativo de notificação para processos externos equivalente ao `LISTEN/NOTIFY` do Postgres (`[09:09] Diego`).

Hoje a aplicação tem um único entry-point, `src/server.ts`, que sobe a API Express e usa o `PrismaClient` criado em `src/config/database.ts`.

## Decisão

1. **Leitura por polling em loop, a cada 2 segundos**, buscando os eventos pendentes mais antigos em lote pequeno (`[09:09] Diego`, `[09:10] Larissa`). A latência mínima de 2 s no pior caso foi explicitamente aceita (`[09:10] Larissa`).
2. **Processo separado da API**: novo entry-point `src/worker.ts`, executado por um script `npm run worker` (`[09:11] Diego`, `[09:11] Larissa`). A lógica de processamento fica dentro do módulo, em `src/modules/webhooks/webhook.processor.ts` (`[09:28] Bruno`).
3. **Mesmo banco e mesma stack, instância própria de `PrismaClient`** — o worker usa a mesma `DATABASE_URL`, mas cria seu próprio client, pois `PrismaClient` é por processo (`[09:30] Bruno`).
4. **Single-worker**: só uma instância roda por vez. A ordenação de entrega é garantida apenas por `order_id` e enquanto houver um único worker; isso é registrado como **limitação conhecida** (`[09:12] Diego`, `[09:13] Larissa`).

## Alternativas Consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| **Trigger no banco para reagir à inserção** | Trigger no MySQL só executa SQL e não notifica processo externo; seria preciso improvisar (escrever em arquivo, chamar endpoint), o que "fica esquisito" (`[09:09] Bruno`, `[09:09] Diego`). |
| **Worker dentro do processo da API** | Se a API reinicia, o worker morre junto (`[09:11] Diego`). |
| **Múltiplos workers em paralelo** | Perde a garantia de ordenação por pedido; escalar exigiria particionar por `order_id` ou lock pessimista — adiado como "problema do futuro" (`[09:13] Diego`). |

## Consequências

**Positivas**

- Latência de detecção ≤ 2 s, bem abaixo do limite de 10 s dos clientes (`[09:09] Diego`).
- API e worker têm ciclo de vida independentes: deploy/restart da API não interrompe entregas.
- Nenhuma dependência nova: reaproveita `createPrismaClient()` de `src/config/database.ts` e o padrão de bootstrap/shutdown de `src/server.ts`.

**Negativas / trade-offs**

- Polling gera consultas constantes ao MySQL mesmo sem eventos — aceito porque a consulta é indexada e o volume é baixo.
- Throughput limitado a um processo; escalar horizontalmente exigirá uma nova decisão (particionamento ou lock).
- Um novo processo para operar, monitorar e manter em execução.
- Ordenação global **não** é garantida — os clientes não pediram (`[09:14] Marcos`).
