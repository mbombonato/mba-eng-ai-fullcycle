# 0005. Resiliência: timeout, retry, fallback técnico e fallback com modelo fraco por feature

- Status: aceita
- Data: 2026-11-09
- Nível: solução

## Contexto

Na v1, com a Anthropic em `error_500`, a F2 devolveu `500` depois de 3 chamadas ao provider (1 + 2 retries automáticos do SDK) e com a OpenAI em `timeout` a F1 ficou pendurada até a borda devolver `504` em 30 s (o SDK esperaria até 600 s, três vezes). Metade do helpdesk para quando um provider para.

Fatos que sustentam a política:

- Os `large` dos dois providers são equivalentes (mesma saída). Um fallback técnico entre eles não muda o resultado.
- Os `mini` foram comparados com os `large` chamando cada tarefa direto no provider simulado com os mesmos 200 primeiros tickets de `data/tickets.jsonl` (e um lote de 150 tickets para `topics`):

| Tarefa | `large` × `mini` |
|---|---|
| `classify` | 0 divergências em 200 tickets: mesma categoria e prioridade |
| `topics` | lote de 150 tickets: saída idêntica; 2,7 s no mini contra 9,8 s no large |
| `suggest` | mesma abertura e mesmos passos, mas texto mais curto: ~1.066 contra ~2.402 caracteres (2,1 s contra 15,8 s) |
| `extract` | 60 divergências em 200: em 31 o `order_number` está errado (o mini pega o primeiro número de 6 dígitos, que costuma ser a nota fiscal) e em 37 o `product` vira `null`. Ex.: TK-00002 "nota fiscal 530720 … pedido #605065" → large `#605065`, mini `#530720` |

- Retries configurados em mais de um lugar se multiplicam.

## Opções consideradas

1. Retry e fallback na aplicação (cada feature trata o próprio erro).
2. Retry, timeout por destino e fallback no gateway; aplicação só com timeout total e tradução de erro.
3. Sem fallback com modelo fraco em nenhuma feature (falhar sempre que os `large` caírem).
4. Fallback com modelo fraco em todas as features.

## Decisão

Opção 2 para o mecanismo; para o modelo fraco, decisão por feature (nem 3 nem 4).

Onde mora cada mecanismo:

| Mecanismo | Onde | Configuração |
|---|---|---|
| Timeout por destino | gateway | `timeout` (e `stream_timeout` na F2) de cada entrada em `gateway/config.yaml`: 4 s F1/F4, 4 s até o primeiro trecho na F2, 20 s por lote na F3 |
| Retry limitado com backoff | gateway | `router_settings.num_retries: 1` e `retry_policy`: 5xx e 429 têm 1 retry; timeout, 400 e 401 não têm. Backoff exponencial do LiteLLM (0,5 s × 2ⁿ + jitter de até 0,75 s) ou o `Retry-After` do provider |
| Fallback técnico | gateway | `router_settings.fallbacks`: primário → large do outro provider, para as 4 capacidades |
| Fallback com modelo fraco | gateway | último item da lista de fallbacks, só em F1, F2 e F3 |
| Timeout total da chamada | aplicação | `REALTIME_TIMEOUT_SECONDS=12` (F1, F2 por trecho, F4) e `REPORT_CALL_TIMEOUT_SECONDS=50` (F3) |
| Retry no SDK | desligado | `max_retries=0` no cliente do gateway (`adapters/gateway.py`) e `litellm_settings.num_retries: 0` |
| Prazo da tarefa F3 | aplicação | `REPORT_DEADLINE_SECONDS=55` |

Número máximo de tentativas por destino (por chamada da aplicação; na F3, por lote):

| Falha | Primário | Fallback técnico | Modelo fraco |
|---|---|---|---|
| `5xx` / `429` | 2 | 2 | 2 |
| timeout | 1 | 1 | 1 |

Fallback com modelo fraco, feature por feature (a pergunta: uma resposta pior é melhor que nenhuma, para quem consome?):

- F1 Classificar: sim, `gpt-fake-mini`. O mini classificou igual ao large em 200 de 200 tickets; para o cliente esperando a confirmação, falhar seria pior e não há perda observável.
- F2 Sugerir resposta: sim, `claude-fake-mini`. O texto sai mais curto (~1.000 contra ~2.400 caracteres), mas com a mesma abertura e os mesmos passos certos para a categoria, e quem consome é um atendente humano que lê e edita antes de enviar. Um rascunho menor ajuda mais que uma tela de erro.
- F3 Relatório: sim, `claude-fake-mini`. A saída de `topics` foi idêntica no lote medido, e o relatório não alimenta decisão automática.
- F4 Extrair dados: não. O mini errou o número do pedido em 31 de 200 tickets (15,5 %) e perdeu o produto em 37, justamente nos tickets que citam nota fiscal. A saída alimenta uma troca automática sem revisão humana: um campo errado vira troca errada (frete, estoque, cliente). Sem `large`, a F4 responde `503` explícito e a automação tenta depois.

## Consequências

- Uma queda de provider custa ao usuário a latência das tentativas no primário (~1 a 2 s) e nada mais; não derruba metade do helpdesk.
- A política de cada feature muda editando a lista `fallbacks` do gateway, sem deploy da aplicação.
- Não há circuit breaker (fora de escopo; `disable_cooldowns: true`): durante uma queda longa, cada requisição paga de novo as tentativas no primário.
- Com timeouts por destino de 4 s, a pior cadeia da F1 (três destinos travados) é ~12 s; a aplicação corta em 12 s e devolve `503`, dentro dos 15 s.

## Evidência

Com o provider simulado (comandos no README, "Tabela de fallback"):

- OpenAI em `error_500`, F1: `/admin/calls` mostra `gpt-fake-large 500`, `gpt-fake-large 500`, `claude-fake-large 200` (duas tentativas no primário com backoff, depois o fallback técnico).
- Os dois `large` em `error_500`: F1 responde `200` com `gpt-fake-mini`; F2 faz streaming com `claude-fake-mini`; F3 termina com `claude-fake-mini`; F4 responde `503` e `/admin/calls` não tem nenhuma chamada a modelo `mini` com task `extract`.
- OpenAI em `timeout`, F1: uma tentativa em `gpt-fake-large` (cortada em 4 s), sucesso em `claude-fake-large`, resposta em ~5 s.
- Testes automatizados: `tests/acceptance/test_failures.py`.
