# Da Reunião ao Documento — Design Docs do Sistema de Webhooks

Entrega do desafio do módulo **Design Docs com IA** (MBA Engenharia de Software com IA — Full Cycle). O enunciado original está em [`ENUNCIADO.md`](ENUNCIADO.md).

## Sobre o desafio

Uma empresa que opera um Order Management System (Node.js + TypeScript + Express + Prisma/MySQL) decidiu, numa reunião de ~55 minutos entre Tech Lead, PM, dois engenheiros e Segurança, construir um **sistema de webhooks outbound** para avisar clientes B2B quando o status de um pedido muda. Nada foi registrado além da transcrição literal da call ([`TRANSCRICAO.md`](TRANSCRICAO.md)).

A tarefa foi transformar essa transcrição, cruzada com o código real da aplicação, num pacote de design docs acionável — PRD, RFC, FDD, ADRs e um Tracker de rastreabilidade — sem inventar requisitos: toda afirmação precisa apontar para uma fala (`[hh:mm] Nome`) ou para um arquivo do repositório. O trabalho foi, sobretudo, de **filtragem** (o que foi decidido, o que foi descartado, o que ficou em aberto) e de **fronteira** entre documentos (cada um responde a uma pergunta diferente).

## Ferramentas de IA utilizadas

| Ferramenta | Papel |
| --- | --- |
| **Claude Code (modelo Claude Opus)** | Agente principal: leu o código (`src/`, `prisma/`, `tests/`), a transcrição e o enunciado direto no repositório, extraiu decisões/descartes, redigiu todos os documentos e executou as checagens automáticas. |
| **Subagente orquestrador do Claude Code** | Distribuiu os desafios do MBA em pastas isoladas do monorepo e passou o briefing do desafio (prompt 1 abaixo), com a restrição de não tocar em código nem em git. |
| **Script Python de verificação (gerado pela IA, executado localmente)** | "Juiz" anti-alucinação: valida que cada `[hh:mm] Nome` do Tracker existe de fato na transcrição com aquele falante, que cada caminho `CODIGO` existe, que todo ID dos documentos está no Tracker (e vice-versa), que as âncoras dos links resolvem e calcula o percentual de linhas `TRANSCRICAO`. |

## Workflow adotado

Segui a ordem sugerida no enunciado, com uma etapa de inventário antes de escrever qualquer documento:

1. **Contextualização** — leitura integral de `ENUNCIADO.md`, `TRANSCRICAO.md` e do código. Do código, mapeei os pontos de integração reais: `changeStatus` em `src/modules/orders/order.service.ts`, a máquina de estados em `src/modules/orders/order.status.ts`, `AppError`/`http-errors.ts`, `errorMiddleware`, `requireRole`, o logger Pino com `redact`, `createPrismaClient()` e o bootstrap de `src/server.ts`.
2. **Inventário da transcrição** — classificação de cada fala relevante em *decisão fechada*, *requisito*, *restrição*, *descartado*, *adiado* ou *não discutido* (prompt 2).
3. **ADRs primeiro** — 7 ADRs: as 6 decisões principais + uma secundária (snapshot do payload e filtro na inserção), porque ela tem alternativas reais discutidas.
4. **RFC** — consolidação em nível de arquitetura, com 6 alternativas descartadas e 9 questões em aberto, linkando os ADRs. Mantido curto de propósito: nenhum schema, payload ou código.
5. **FDD** — schema Prisma, 5 fluxos, 8 contratos com exemplos, matriz `WEBHOOK_*`, observabilidade, resiliência e a seção "Integração com o sistema existente" com 14 arquivos reais.
6. **PRD** — por último entre os grandes, como consolidação em linguagem de produto.
7. **Tracker** — IDs foram colocados *dentro* dos documentos (`PRD-FR-01`, `FDD-CONTRATO-03`…) para que cada linha do Tracker aponte para algo localizável; depois rodei o script de verificação (prompt 3).
8. **Revisão final** item a item contra os critérios de aceite.

## Prompts customizados

**Prompt 1 — briefing do desafio (orquestrador → agente)**

```text
Você vai implementar UM desafio do MBA Full Cycle "Engenharia de Software com IA" dentro de um monorepo.
Responda/escreva em pt-BR (com acentuação correta); identificadores de código em inglês.

Pasta de trabalho EXCLUSIVA: 05-design-docs-com-ia
- Leia ENUNCIADO.md inteiro, TRANSCRICAO.md inteira e o código da aplicação (src/, prisma/, docs/)
  antes de começar — os documentos precisam ser fiéis à aplicação real e à transcrição.
- NÃO edite nada fora dessa pasta. NÃO rode git commit/push/reset/checkout.
- Entregue exatamente o pacote pedido: docs/PRD.md, docs/RFC.md, docs/FDD.md, docs/adrs/ADR-NNN-*.md,
  docs/TRACKER.md e README.md com o processo — seguindo a estrutura obrigatória e TODOS os Critérios
  de Aceite (incluindo "Consistência geral" e rastreabilidade entre documentos).
- Revise ao final, item a item, os critérios de aceite contra o que você produziu.
```

**Prompt 2 — filtragem dirigida da transcrição (em vez de "gere um PRD")**

```text
Leia TRANSCRICAO.md linha a linha. Para CADA fala que contenha conteúdo técnico ou de produto,
classifique em exatamente uma categoria:
  DECISAO_FECHADA | REQUISITO_FUNCIONAL | REQUISITO_NAO_FUNCIONAL | RESTRICAO |
  DESCARTADO (alternativa rejeitada + motivo) | ADIADO (fase futura / "observar") | NAO_DECIDIDO
Formato: [hh:mm] Nome | categoria | resumo em 1 linha | quem confirmou a decisão (se houver).
Regras:
- Proposta que alguém fez e foi corrigida depois (ex.: customer_id "implícito do JWT") deve
  aparecer com a correção, nunca com a versão original.
- Se duas falas parecem conflitar (ex.: "5 tentativas" x 5 intervalos de backoff), NÃO resolva:
  marque como NAO_DECIDIDO e explique a ambiguidade.
- Liste à parte qualquer interação entre decisões que a reunião NÃO discutiu
  (ex.: ordenação por order_id x reagendamento por retry).
Depois, para cada item, aponte o arquivo do código que ele toca (caminho real em src/ ou prisma/).
```

**Prompt 3 — auditoria anti-alucinação do pacote**

```text
Atue como revisor cético do pacote em docs/. Para cada documento:
1. Liste toda afirmação que pareça requisito, decisão, número ou restrição e verifique se existe
   origem em TRANSCRICAO.md (timestamp + falante corretos) ou em um arquivo real do repositório.
   Sem origem => remova ou marque explicitamente como "proposta de implementação" a validar.
2. Procure itens que a reunião DESCARTOU ou ADIOU aparecendo como requisito
   (e-mail, dashboard, rate limiting, ordenação global, exactly-once, secret global...).
3. Procure contradições com o código: rotas fora de /api/v1, códigos de erro que o
   validate middleware não consegue emitir, FKs que conflitam com OrderService.delete etc.
4. Gere um script Python que valide o TRACKER.md: pares [hh:mm] Nome existentes na transcrição,
   caminhos CODIGO existentes, IDs dos docs ⇄ IDs do tracker, % de linhas TRANSCRICAO,
   âncoras dos links entre documentos. Rode e corrija tudo o que falhar.
```

## Iterações e ajustes

Foram **4 ciclos principais** (inventário → ADRs/RFC → FDD/PRD → tracker + auditoria). Os ajustes mais relevantes:

1. **Requisito inventado removido.** A primeira versão da estratégia de testes do PRD trazia uma "validação com cliente piloto (Atlas)". Não há essa fala na reunião — o Marcos só fala de prazo. Troquei pela sessão de revisão do design com Bruno e Diego, que existe (`[09:50] Larissa`).
2. **`customer_id` no lugar certo.** O rascunho do RFC propunha o `customerId` como *query param* na listagem. A Larissa disse "no body ou no path" (`[09:32] Larissa`), então a listagem virou `GET /customers/:customerId/webhooks`. A primeira fala do Marcos ("implícito do JWT") foi descartada porque o Bruno e a Larissa a corrigiram em seguida.
3. **Limite de 64 KB no ponto certo.** A primeira ideia era validar o tamanho na inserção da outbox, mas isso lançaria erro dentro da transação de `changeStatus` e faria rollback da mudança de status por causa de um webhook, justamente o acoplamento que o Bruno rejeitou (`[09:04] Bruno`). A checagem foi movida para o worker, com DLQ imediata.
4. **Ambiguidades expostas, não escondidas.** A IA tinha escrito "5 tentativas" sem perceber que 5 intervalos somando ~15 h só fecham com envio inicial + 5 retentativas. Isso virou interpretação explícita no ADR-003 e questão RFC-QA-07. Da mesma forma, a interação entre ordenação por `order_id` e retry, que a reunião não tratou, virou RFC-QA-06.
5. **Conflito com o código.** O código de erro `WEBHOOK_INVALID_URL` (`[09:28] Bruno`) não chegaria ao cliente se a regra `https` ficasse só no Zod, porque `validate.middleware.ts` converte qualquer `ZodError` em `VALIDATION_ERROR`. O FDD documenta como o service emite o código específico. Outro caso: a FK de `webhook_outbox.orderId` foi removida porque `OrderService.delete` permite excluir pedidos `CANCELLED`, e o cascade apagaria eventos pendentes.
6. **Arquivos inexistentes.** O script apontou `src/worker.ts` e `src/modules/webhooks/*` como caminhos inexistentes. Todas as menções foram marcadas como "novo/a criar", e o Tracker usa apenas caminhos reais em linhas `CODIGO`. O `docs/adrs/README.md` do boilerplate sugeria a nomenclatura `0001-titulo.md`, que conflitava com a exigida (`ADR-NNN-…`), e foi atualizado como índice.

Resultado da última execução do verificador: 269 linhas no Tracker (≈ 89% `TRANSCRICAO`, 30 `CODIGO`), 100% dos IDs dos documentos rastreados, 0 timestamps inválidos, 0 links quebrados.

## Como navegar a entrega

Ordem sugerida de leitura:

| # | Arquivo | O que responde |
| --- | --- | --- |
| 1 | [`docs/PRD.md`](docs/PRD.md) | Por que e o quê: problema, público, métricas, escopo e fora de escopo |
| 2 | [`docs/RFC.md`](docs/RFC.md) | Proposta de arquitetura, alternativas descartadas e questões em aberto |
| 3 | [`docs/adrs/`](docs/adrs/README.md) | Uma decisão por arquivo (ADR-001 a ADR-007) |
| 4 | [`docs/FDD.md`](docs/FDD.md) | Como construir: schema, fluxos, contratos, erros, observabilidade, integração com o código |
| 5 | [`docs/TRACKER.md`](docs/TRACKER.md) | De onde veio cada item (transcrição ou código) |
| — | [`TRANSCRICAO.md`](TRANSCRICAO.md) · [`ENUNCIADO.md`](ENUNCIADO.md) | Fontes originais |

ADRs:

- [ADR-001 — Outbox transacional no MySQL](docs/adrs/ADR-001-outbox-transacional-no-mysql.md)
- [ADR-002 — Worker separado com polling de 2 s](docs/adrs/ADR-002-worker-separado-com-polling.md)
- [ADR-003 — Retry com backoff exponencial e DLQ](docs/adrs/ADR-003-retry-com-backoff-exponencial-e-dlq.md)
- [ADR-004 — HMAC-SHA256 com secret por endpoint](docs/adrs/ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md)
- [ADR-005 — At-least-once com `X-Event-Id`](docs/adrs/ADR-005-entrega-at-least-once-com-x-event-id.md)
- [ADR-006 — Reuso dos padrões existentes](docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md)
- [ADR-007 — Snapshot do payload e filtro na inserção](docs/adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md)

> A aplicação (`src/`, `prisma/`, `tests/`, configurações) não foi alterada. A entrega é só documentação.
