# Da Reunião ao Documento: Design Docs do Sistema de Webhooks

Entrega do desafio do módulo Design Docs com IA (MBA Engenharia de Software com IA, Full Cycle). O enunciado original está em [`ENUNCIADO.md`](ENUNCIADO.md).

## Sobre o desafio

Uma empresa que opera um Order Management System (Node.js, TypeScript, Express, Prisma/MySQL) decidiu, numa reunião de cerca de 55 minutos, construir um sistema de webhooks para avisar clientes B2B quando o status de um pedido muda. O único registro é a transcrição da call ([`TRANSCRICAO.md`](TRANSCRICAO.md)).

A tarefa foi transformar essa transcrição, cruzada com o código da aplicação, em um pacote de design docs: PRD, RFC, FDD, ADRs e um Tracker de rastreabilidade. Nenhum requisito pode ser inventado: cada item aponta para uma fala (`[hh:mm] Nome`) ou para um arquivo do repositório. A aplicação (`src/`, `prisma/`, `tests/`, configurações) não foi alterada; a entrega é só documentação.

## Como navegar a entrega

Ordem sugerida de leitura:

| # | Arquivo | O que responde |
| --- | --- | --- |
| 1 | [`docs/PRD.md`](docs/PRD.md) | Por que e o quê: problema, público, métricas, escopo e fora de escopo |
| 2 | [`docs/RFC.md`](docs/RFC.md) | Proposta de arquitetura, alternativas descartadas e questões em aberto |
| 3 | [`docs/adrs/`](docs/adrs/README.md) | Uma decisão por arquivo (ADR-001 a ADR-007) |
| 4 | [`docs/FDD.md`](docs/FDD.md) | Como construir: schema, fluxos, contratos, erros, observabilidade, integração com o código |
| 5 | [`docs/TRACKER.md`](docs/TRACKER.md) | De onde veio cada item (transcrição ou código) |

ADRs:

- [ADR-001: Outbox transacional no MySQL](docs/adrs/ADR-001-outbox-transacional-no-mysql.md)
- [ADR-002: Worker separado com polling de 2 s](docs/adrs/ADR-002-worker-separado-com-polling.md)
- [ADR-003: Retry com backoff exponencial e DLQ](docs/adrs/ADR-003-retry-com-backoff-exponencial-e-dlq.md)
- [ADR-004: HMAC-SHA256 com secret por endpoint](docs/adrs/ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md)
- [ADR-005: At-least-once com `X-Event-Id`](docs/adrs/ADR-005-entrega-at-least-once-com-x-event-id.md)
- [ADR-006: Reuso dos padrões existentes](docs/adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md)
- [ADR-007: Snapshot do payload e filtro na inserção](docs/adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md)

## Ferramentas de IA utilizadas

| Ferramenta | Papel |
| --- | --- |
| Claude Code (modelo Claude Opus) | Usado para ler o código e a transcrição, redigir os documentos e rodar as checagens. |
| Script Python de verificação (gerado pela IA, executado localmente) | Confere o Tracker: pares `[hh:mm] Nome` existentes na transcrição, caminhos `CODIGO` existentes, IDs dos documentos presentes no Tracker e vice-versa, âncoras dos links e percentual de linhas `TRANSCRICAO`. |

Limitações do script: não foi versionado e a checagem é sintática, ou seja, não avalia se a fala sustenta o item.

## Workflow adotado

Segui a ordem sugerida no enunciado, com uma etapa de inventário antes de escrever qualquer documento:

1. Contextualização: leitura de `ENUNCIADO.md`, `TRANSCRICAO.md` e do código, mapeando os pontos de integração (`changeStatus` em `src/modules/orders/order.service.ts`, a máquina de estados em `src/modules/orders/order.status.ts`, classes de erro, middlewares, logger e bootstrap de `src/server.ts`).
2. Inventário da transcrição: classificação de cada fala relevante em decisão fechada, requisito, restrição, descartado, adiado ou não decidido (prompt 1).
3. ADRs: 7 no total, as 6 decisões principais e uma secundária (snapshot do payload e filtro na inserção).
4. RFC: proposta em nível de arquitetura, com 6 alternativas descartadas e 9 questões em aberto, com links para os ADRs.
5. FDD: schema Prisma, 5 fluxos, 7 endpoints HTTP com exemplos, o contrato da requisição enviada ao cliente, matriz `WEBHOOK_*`, observabilidade, resiliência e a seção "Integração com o sistema existente", com 14 arquivos reais.
6. PRD: por último entre os grandes, como consolidação em linguagem de produto.
7. Tracker: PRD, RFC e FDD trazem os IDs no próprio texto (`PRD-FR-01`, `FDD-CONTRATO-03`). Nos ADRs, os sub-itens (`ADR-NNN-ALT-NN`, `ADR-NNN-CONS-NN`) seguem a ordem das linhas de cada ADR, sem ID escrito no arquivo. Depois rodei o script de verificação (prompt 2).
8. Revisão final, item a item, contra os critérios de aceite.

## Prompts customizados

Prompt 1: filtragem dirigida da transcrição (em vez de "gere um PRD")

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

Prompt 2: auditoria do pacote e verificação do Tracker

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

Foram 4 ciclos principais: inventário, ADRs e RFC, FDD e PRD, Tracker e auditoria. Os ajustes mais relevantes:

1. Requisito inventado. A primeira versão da estratégia de testes do PRD trazia uma "validação com cliente piloto (Atlas)", que não aparece na reunião. Troquei pela sessão de revisão do design com Bruno e Diego (`[09:50] Larissa`).
2. `customer_id` no lugar errado. O rascunho do RFC colocava o `customerId` como query param na listagem. A Larissa disse "no body ou no path" (`[09:32] Larissa`), então a listagem virou `GET /customers/:customerId/webhooks`. A fala anterior do Marcos ("implícito do JWT") foi descartada porque Bruno e Larissa a corrigiram em seguida.
3. Limite de 64 KB. A primeira ideia era validar o tamanho na inserção da outbox, mas o erro ocorreria dentro da transação de `changeStatus` e desfaria a mudança de status, o acoplamento que o Bruno rejeitou (`[09:04] Bruno`). A checagem foi para o worker, com DLQ imediata.
4. Ambiguidades da reunião. A IA escreveu "5 tentativas" sem notar que 5 intervalos somando cerca de 15 h só fecham com envio inicial mais 5 retentativas. Isso virou interpretação explícita no ADR-003 e a questão RFC-QA-07. A interação entre ordenação por `order_id` e retry, que a reunião não tratou, virou RFC-QA-06.
5. Conflito com o código. O erro `WEBHOOK_INVALID_URL` (`[09:28] Bruno`) não chegaria ao cliente se a regra `https` ficasse só no Zod, porque `validate.middleware.ts` converte qualquer `ZodError` em `VALIDATION_ERROR`; o FDD documenta como o service emite o código específico. A FK de `webhook_outbox.orderId` foi removida porque `OrderService.delete` permite excluir pedidos `CANCELLED` e o cascade apagaria eventos pendentes.
6. Arquivos inexistentes. O script apontou `src/worker.ts` e `src/modules/webhooks/*` como caminhos que não existem. As menções foram marcadas como "novo/a criar" e o Tracker usa só caminhos reais nas linhas `CODIGO`. O `docs/adrs/README.md` do repositório base sugeria a nomenclatura `0001-titulo.md`, diferente da exigida (`ADR-NNN-…`), e foi atualizado como índice.

Última execução do verificador: 269 linhas no Tracker (239 `TRANSCRICAO`, 30 `CODIGO`), todos os IDs dos documentos presentes no Tracker, todos os pares `[hh:mm] Nome` existentes na transcrição e nenhum link quebrado.
