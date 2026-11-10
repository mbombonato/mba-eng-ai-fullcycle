# 0004. Modo de execução de cada feature

- Status: aceita
- Data: 2026-11-09
- Nível: solução

## Contexto

Na v1, as quatro features respondem de forma síncrona e sem timeout próprio (valem os 600 s dos SDKs). A borda (`edge/nginx.conf`) encerra com `504` qualquer requisição que passe 30 s sem receber byte, e não cancela o que a aplicação está fazendo. Medido no diagnóstico:

| Feature | Latência na v1 (modo normal) | Saída |
|---|---|---|
| F1 | 1,1 s | JSON curto, valores fixos |
| F2 | 16,0 s até o primeiro byte (resposta inteira de uma vez) | ~2.400 caracteres de texto |
| F3 (mês) | `504` em 30 s; 34 lotes de ~9,8 s em série, ~5,5 min no total | relatório agregado |
| F4 | 1,1 s | JSON com dois campos |

Requisitos de experiência: F1 em até 3 s; F2 com o primeiro trecho em até 1,5 s; F3 aceita em até 1 s e o relatório completo fica disponível depois; nenhuma resposta em `504`; síncronos com timeout explícito, respondendo em até 15 s mesmo com o provider travado.

A árvore de decisão usada em cada feature: (1) alguém está esperando agora? (2) cabe no orçamento de latência? (3) o resultado é consumível aos poucos?

## Opções consideradas

Para cada feature: síncrono com timeout, streaming (SSE) ou assíncrono (Asynchronous Request-Reply). Para o assíncrono: tarefa em memória no processo da aplicação, ou fila + worker em serviços separados.

## Decisão

### F1 Classificar ticket: síncrono, com timeout explícito

- Alguém está esperando agora? Sim: o cliente está na tela esperando a confirmação da abertura do ticket.
- Cabe no orçamento de latência? Sim: ~1,1 s contra 3 s, sobrando margem para um retry rápido.
- É consumível aos poucos? Não: `{"category", "priority"}` é saída curta de valores fixos; meio JSON não serve para nada.

Síncrono. Timeout de 4 s por destino no gateway (sem retry em timeout) e teto de 12 s na aplicação (`REALTIME_TIMEOUT_SECONDS`): com o primário travado, o fallback responde em ~5 s; se toda a cadeia travar, a aplicação devolve `503` explícito antes de 15 s e muito antes dos 30 s da borda.

### F2 Sugerir resposta: streaming (SSE)

- Alguém está esperando agora? Sim: o atendente olha a tela e começa a ler e editar assim que o texto aparece.
- Cabe no orçamento de latência? Não como resposta inteira: o texto completo leva ~16 s, contra 1,5 s para o primeiro trecho (e 16 s deixa pouca margem para os 30 s da borda).
- É consumível aos poucos? Sim: é texto corrido, lido na ordem em que é gerado.

Streaming SSE (`Content-Type: text/event-stream`), no formato de Contratos sugeridos: `data: {"chunk": ...}` por trecho e `event: end` no fim. O assíncrono não serve: liberaria a conexão, mas o atendente continuaria sem ver nada até o fim. O que é necessário para o streaming atravessar a borda:

- A resposta leva `X-Accel-Buffering: no`, que desliga o buffer do nginx da borda só para ela (a borda não pode ser alterada; o header é o mecanismo que o próprio nginx oferece para o upstream).
- A aplicação espera o primeiro trecho antes de responder. Se nenhum destino atender, o cliente recebe `503` (ou `429`, recusa de governança) explícito, em vez de um `200` com stream vazio.
- Erro depois do primeiro trecho (o `200` já foi enviado): a aplicação emite `event: error` com `{"ticket_id", "message": "A geração foi interrompida"}` e encerra o stream.
- Um stream que para de chegar é cortado pelo timeout de leitura do cliente do gateway (12 s sem trecho) e vira o mesmo evento `error`: o stream nunca fica 30 s mudo.

### F3 Relatório de temas: assíncrono (Asynchronous Request-Reply)

- Alguém está esperando agora? Não: quem pede é um painel interno, e ninguém fica olhando para ele.
- Cabe no orçamento de latência? Não: o mês são 5.000 tickets em 34 lotes de ~9,8 s cada; em série são ~5,5 min, muito além dos 30 s da borda.
- É consumível aos poucos? Não: um relatório de contagens só faz sentido completo (a contagem de um tema muda até o último lote).

Asynchronous Request-Reply com polling, porque o painel roda no navegador e não expõe callback: `POST /reports/topics` valida a entrada (erros continuam `422` síncronos) e responde `202 Accepted` com `Location: /reports/topics/status/{id}` e `Retry-After: 5`. A URL de status responde `200` com `{"state": "pending" | "running" | "failed", "progress": "n/5000", "reason"}` e `303 See Other` para `/reports/topics/{id}` quando a tarefa chega a `done`. O corpo do `202` traz também `id`, `state` e `status_url`, por conveniência.

Como a tarefa roda:

- Em memória, numa thread da própria aplicação (`jobs.py`). Uma fila com worker (serviços extras) resolveria sobrevivência a reinício e escala horizontal, que o enunciado deixa fora de escopo; aqui seriam duas peças a mais a operar sem requisito que as justifique.
- Os lotes vão até 12 ao mesmo tempo (`REPORT_CONCURRENCY`): o mês termina em cerca de 30 a 35 s em vez de ~5,5 min. Os resultados são somados na ordem dos lotes, então o relatório é o mesmo da execução em série (a suíte de caracterização confere isso no período de 2 dias, com 2 lotes).
- Prazo da tarefa: 55 s (`REPORT_DEADLINE_SECONDS`). Falha de um lote (depois de todo o retry e fallback do gateway), recusa de orçamento ou prazo estourado levam a tarefa a `failed` com o motivo, e os lotes que ainda não começaram são cancelados. Uma tarefa nunca fica presa em `running` e chega a `failed` antes de 60 s.

### F4 Extrair dados do pedido: síncrono, com timeout explícito

- Alguém está esperando agora? Sim: uma automação de troca e devolução espera os campos para seguir.
- Cabe no orçamento de latência? Sim: ~1,1 s.
- É consumível aos poucos? Não: dois campos que só valem juntos e validados (`#` + 6 dígitos).

Síncrono, com os mesmos timeouts da F1 (4 s por destino no gateway, 12 s na aplicação). Sem fallback com modelo fraco (ADR 0005): sem `large` disponível, responde `503` explícito, e a automação tenta de novo depois.

## Consequências

- O contrato da F2 e da F3 mudou (evolução deliberada, depois da tag `v2-decoupled`). Na `main`, os testes de caracterização dessas duas features foram atualizados para o novo contrato, com o mesmo texto e o mesmo relatório fixados na v1.
- O estado das tarefas da F3 vive no processo: reiniciar a aplicação perde as tarefas em andamento (fora de escopo) e não há deduplicação de pedidos iguais (fora de escopo).
- Desistir não é cancelar: quando a F3 falha, até 12 lotes que já estavam em voo terminam no provider. O custo máximo desse resto é limitado e está coberto pelo orçamento da chave de relatórios.
- Não há cancelamento da geração quando o cliente fecha o stream da F2 (fora de escopo).

## Evidência

- `tests/acceptance/test_flows.py`: F1 ≤ 3 s; F2 primeiro trecho ≤ 1,5 s e antes da metade do tempo total; F3 aceita em ≤ 1 s e relatório com `total_tickets` 5000, produzido por 34 chamadas `topics` em `/admin/calls`.
- `tests/acceptance/test_failures.py`: F1 com o primário em `timeout` responde em ~5 s; F3 com os dois providers em `error_500` chega a `failed` com motivo em ~6 s; F2 com o primário em `midstream_error` termina com `event: error`.
- Os `curl` exatos de cada fluxo estão na seção "Fluxos" do README.
