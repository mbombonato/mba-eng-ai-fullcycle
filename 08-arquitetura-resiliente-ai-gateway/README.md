# Helpdesk com IA: da integração frágil à arquitetura resiliente

Entrega do desafio "Da integração frágil à arquitetura resiliente: IA em produção num helpdesk". O enunciado está em [`ENUNCIADO.md`](ENUNCIADO.md).

## Visão geral

O helpdesk tem quatro features com IA: classificar ticket (F1), sugerir resposta (F2), relatório de temas (F3) e extrair dados do pedido (F4). Na versão recebida, cada feature chamava o SDK do provider direto, com o nome do modelo e as chaves no código, tudo síncrono e sem timeout próprio. Agora a aplicação (`app/`, FastAPI) pede capacidades lógicas (`ticket-classification`, `reply-suggestion`, `topics-report`, `order-extraction`) a um AI Gateway self-hosted (LiteLLM Proxy, serviço `gateway`), usando chaves virtuais do próprio gateway. Só o gateway conhece providers, modelos físicos, chaves dos providers, preços, orçamentos, limites, timeouts, retries e fallbacks. F1 e F4 são síncronas com timeout, F2 responde em streaming (SSE) e F3 é assíncrona (Asynchronous Request-Reply).

Quando um provider responde com erro (`error_500`), o gateway tenta o primário no máximo 2 vezes, com backoff, e segue para o modelo `large` equivalente do outro provider. As quatro features continuam respondendo, com a mesma saída, ~1 a 2 s mais lentas. Se os dois `large` caírem, F1, F2 e F3 respondem com um modelo `mini` e a F4 falha com `503`, porque o `mini` erra o número do pedido e a extração alimenta uma troca automática (ADR 0005). Nos cenários de falha dos critérios de aceite, nenhuma requisição termina em `504` da borda: as síncronas respondem em até 15 s, o stream nunca fica 30 s mudo e o relatório chega a `failed` com motivo em menos de 60 s.

```
cliente ──> edge (nginx, :8000) ──> app (FastAPI, :8080) ──> gateway (LiteLLM, :4000) ──> provider-fake (:8090)
                                         │ chaves virtuais           │ chaves dos providers, preços,
                                         │ capacidades lógicas       │ retry, fallback, orçamento, limite
                                                                     └──> gateway-db (Postgres)
```

O código que chama o gateway fica num único componente: `app/helpdesk/adapters/gateway.py` (`GatewayTextModel`, SDK `openai` apontado para `http://gateway:4000/v1`). Nenhuma feature o importa; só o ponto de composição `app/helpdesk/main.py` depende dele.

Limitações conhecidas:

- Com um provider em `timeout` (sem resposta), cada destino consome o próprio timeout antes do fallback. O relatório do mês inteiro pode não caber no prazo da tarefa e, nesse caso, termina em `failed` com motivo.
- As tarefas da F3 ficam em memória: um reinício da aplicação perde as que estão em andamento (ADR 0004).
- Durante os segundos em que o gateway reinicia, as features respondem `503`.

## Diagnóstico da v1

Reproduzido na tag `v1-coupled` (`app/` idêntico ao do repositório base), pela borda `localhost:8000`, com o provider simulado no modo normal salvo indicação. Os horários de `/admin/calls` são UTC.

### Dor 1: o relatório do mês nunca chega

```
curl -s -w '\nstatus %{http_code} total %{time_total}s\n' -X POST localhost:8000/reports/topics \
  -H "Content-Type: application/json" -d '{"start": "2026-08-01", "end": "2026-08-31"}'
curl -s "localhost:8090/admin/calls?last=50"
```

Observado:

- A borda devolveu `504 Gateway Time-out` em 30,03 s.
- `/admin/calls` mostrou 34 chamadas `anthropic claude-fake-large topics`, em série, de ~9,8 s cada: a primeira às 20:15:32 e a última terminando às ~20:21:04. A aplicação continuou trabalhando por mais de 5 minutos depois que a borda já tinha desistido.
- Essas 34 chamadas consumiram 222.114 tokens de entrada e 12.162 de saída (≈ US$ 0,85 pela tabela do provider), pagos por um relatório que ninguém recebeu.

Causa no código (`v1-coupled`):

- `app/helpdesk/report.py`, linhas 15-18: um lote de 150 tickets por chamada, um depois do outro (`for first in range(...)` com `llm.call_anthropic` síncrono). O mês tem 5.000 tickets = 34 lotes = ~5,5 min.
- `app/helpdesk/main.py`, linhas 30-32: a rota é síncrona e só responde quando o relatório inteiro termina, muito além dos 30 s de `proxy_read_timeout` da borda (`edge/nginx.conf`).

### Dor 2: a sugestão de resposta deixa o atendente olhando uma tela parada

```
curl -s -o /dev/null -w 'status %{http_code} primeiro byte %{time_starttransfer}s total %{time_total}s bytes %{size_download}\n' \
  -X POST localhost:8000/tickets/reply-suggestion -H "Content-Type: application/json" \
  -d '{"ticket_id": "TK-00042", "text": "Meu pedido #481516 não chegou e já passou do prazo, urgente"}'
```

Observado: `status 200 primeiro byte 15,96s total 15,96s bytes 2606`. Nada chega ao cliente durante 16 s e depois chega tudo de uma vez. `/admin/calls`: uma chamada `anthropic claude-fake-large suggest`, sem stream, 15.951 ms, 606 tokens de saída.

Causa no código: `app/helpdesk/suggestion.py`, linha 6, chama `llm.call_anthropic`, que em `app/helpdesk/llm.py`, linhas 21-26, usa `messages.create` sem `stream=True` e devolve o texto inteiro; `main.py`, linhas 20-22, responde um JSON único. Com 16 s, qualquer lentidão do provider (modo `slow`) também levaria a `504`.

### Dor 3: com um provider fora do ar ou travado, parte do helpdesk para

```
curl -s -X POST localhost:8090/admin/failures -H "Content-Type: application/json" -d '{"provider": "openai", "mode": "error_500"}'
curl -s -w ' %{http_code} %{time_total}s\n' -X POST localhost:8000/tickets/classification -H "Content-Type: application/json" \
  -d '{"ticket_id": "TK-00042", "text": "Meu pedido #481516 não chegou e já passou do prazo, urgente"}'
# o mesmo para /tickets/extraction; depois anthropic em error_500 e /tickets/reply-suggestion
curl -s -X POST localhost:8090/admin/failures -H "Content-Type: application/json" -d '{"provider": "openai", "mode": "timeout"}'
# de novo /tickets/classification
curl -s "localhost:8090/admin/calls?last=50"
```

Observado:

| Cenário | F1 | F4 | F2 | `/admin/calls` |
|---|---|---|---|---|
| OpenAI em `error_500` | `500 Internal Server Error` em 1,47 s | `500` em 1,32 s | `200` (Anthropic) | 3 chamadas `gpt-fake-large` com `500` por requisição (1 + 2 retries automáticos do SDK), nenhuma tentativa em outro provider |
| Anthropic em `error_500` | `200` | — | `500` em 1,37 s | 3 chamadas `claude-fake-large suggest` com `500` |
| OpenAI em `timeout` | `504` da borda em 30,04 s | — | — | a chamada das 20:16:14 ficou presa 300 s (status `504` do provider, `duration_ms` 300.001) e o SDK repetiu às 20:21:14, 5 minutos depois que o cliente já tinha recebido `504` |

Metade do helpdesk (F1 e F4, ou F2 e F3) para junto com um provider, mesmo havendo um modelo equivalente no outro. Com o provider travado, a aplicação fica pendurada além da paciência da borda e continua gastando depois.

Causa no código:

- `app/helpdesk/config.py`, linhas 9-13: cada feature tem provider e modelo fixos (F1/F4 na OpenAI, F2/F3 na Anthropic); não existe destino alternativo.
- `app/helpdesk/llm.py`, linhas 8-9: os clientes são criados sem `timeout` nem `max_retries`, então valem os padrões dos SDKs `openai` e `anthropic`: 600 s de timeout e 2 retries. Uma única requisição pode prender a aplicação por até 3 × 600 s, contra 30 s da borda.

### Dor 4: trocar o modelo de uma feature exige mudar código e reconstruir

Alteração temporária (desfeita antes da tag `v1-coupled`):

```
sed -i 's/^CLASSIFICATION_MODEL = "gpt-fake-large"/CLASSIFICATION_MODEL = "gpt-fake-mini"/' app/helpdesk/config.py
docker compose restart app            # e chama a F1
docker compose up -d --build --wait app   # e chama a F1 de novo
git checkout -- app/helpdesk/config.py && docker compose up -d --build --wait app
```

Observado:

- Depois do `restart`, `/admin/calls` continuou mostrando `gpt-fake-large classify`: o código está copiado dentro da imagem (`app/Dockerfile`, `COPY helpdesk ./helpdesk`).
- Só com rebuild (7,5 s com cache) e um container novo (`b910786cf40a` → `456e179a4c34`) a chamada seguinte foi para `gpt-fake-mini classify`. Trocar um modelo é um deploy.

Causa no código: `app/helpdesk/config.py`, linhas 10-13 (nomes de modelo físico como constantes), consumidos por `classification.py`, `extraction.py`, `suggestion.py` e `report.py`. As chaves dos providers também estão na aplicação (`config.py`, linhas 3-4, vindas do `env_file: .env` do compose).

## Como rodar

Pré-requisitos: Docker com Compose v2. Python 3.12 só para os testes e para o script de métrica. Os comandos rodam a partir desta pasta.

### Subida

```
cp .env.example .env
docker compose up -d --build --wait
curl -s localhost:8000/health
```

Resultado esperado: `{"status":"ok"}`. O primeiro `up` leva ~1 min por causa das migrações do banco do gateway. As chaves virtuais do gateway são criadas no boot, sem passo manual (ADR 0007).

Portas no host: 8000 (borda), 8090 (provider simulado) e 4000 (gateway). Se alguma estiver ocupada, defina `EDGE_PORT`, `PROVIDER_FAKE_PORT` ou `GATEWAY_PORT` no `.env` e passe `HELPDESK_URL`, `PROVIDER_URL` e `GATEWAY_URL` aos testes.

### Testes de caracterização

```
python3 -m venv .venv && .venv/bin/pip install -r tests/requirements.txt
.venv/bin/pytest tests/characterization
```

Rodam contra a aplicação no compose. Resultado esperado na `main`: 18 testes passando. Nas tags `v1-coupled` e `v2-decoupled` a suíte é a mesma (17 testes, contrato síncrono da v1) e passa nas duas. Na `main`, os testes de F2 e F3 seguem o contrato novo (streaming e assíncrono), com o mesmo texto e o mesmo relatório fixados na v1.

### Testes de aceite da `main`

```
.venv/bin/pytest tests/acceptance
```

Cobrem tempos, falhas do provider, fallback e governança. Levam ~2 min.

### Script de métrica

```
python3 metrics/coupling.py app/helpdesk main
```

Para medir uma tag, rode o script desta branch sobre um checkout dela:

```
git worktree add /tmp/v1-coupled v1-coupled
python3 metrics/coupling.py /tmp/v1-coupled/08-arquitetura-resiliente-ai-gateway/app/helpdesk v1-coupled
git worktree remove /tmp/v1-coupled
```

O script usa só a biblioteca padrão. Grava `metrics/results/<nome>.csv` (cabeçalho `component,ca,ce,i,a,d`) e `metrics/results/<nome>.svg` (gráfico A × I com a Main Sequence e as zonas de dor e de inutilidade). O checkout da tag traz o repositório inteiro, por isso o caminho inclui a pasta do desafio.

## Métrica

Régua do requisito 3, script `metrics/coupling.py`, resultados em `metrics/results/`: [v1-coupled](metrics/results/v1-coupled.svg), [v2-decoupled](metrics/results/v2-decoupled.svg) e [main](metrics/results/main.svg).

| Componente | v1-coupled (Ca, Ce, I, A, D) | v2-decoupled | main |
|---|---|---|---|
| `llm` | 4, 1, 0,20, 0, 0,80 (dor) | removido | removido |
| `config` | 6, 0, 0,00, 0, 1,00 (dor) | 1, 0, 0,00, 0, 1,00 (exceção) | 1, 0, 0,00, 0, 1,00 (exceção) |
| `schemas` | 5, 0, 0,00, 0, 1,00 (exceção) | 5, 0, 0,00, 0, 1,00 (exceção) | 6, 0, 0,00, 0, 1,00 (exceção) |
| `errors` | — | — | 6, 0, 0,00, 0, 1,00 (exceção) |
| `ports` | — | 6, 0, 0,00, 1, 0,00 | 6, 0, 0,00, 1, 0,00 |
| `adapters.gateway` | — | 1, 1, 0,50, 0, 0,50 | 1, 2, 0,67, 0, 0,33 |
| `classification` / `extraction` | 1, 3, 0,75, 0, 0,25 | 1, 2, 0,67, 0, 0,33 | 1, 3, 0,75, 0, 0,25 |
| `suggestion` | 1, 3, 0,75, 0, 0,25 | 1, 2, 0,67, 0, 0,33 | 1, 2, 0,67, 0, 0,33 |
| `report` | 1, 4, 0,80, 0, 0,20 | 1, 2, 0,67, 0, 0,33 | 1, 3, 0,75, 0, 0,25 |
| `tickets` | 1, 1, 0,50, 0, 0,50 | 1, 1, 0,50, 0, 0,50 | 1, 1, 0,50, 0, 0,50 |
| `jobs` | — | — | 1, 2, 0,67, 0, 0,33 |
| `main` | 0, 5, 1,00, 0, 0,00 | 0, 8, 1,00, 0, 0,00 | 0, 10, 1,00, 0, 0,00 |

Leitura dos três gráficos:

- v1-coupled: as features estão à direita (I 0,75-0,80), mas apontam para dois componentes concretos, estáveis e cheios de decisões voláteis: `llm` (dois SDKs, um cliente por provider) e `config` (chaves, base URLs, nomes de modelo físico). Os dois estão no canto inferior esquerdo, na zona de dor. É o acoplamento do diagnóstico: trocar modelo ou provider passa por eles e pede deploy.
- v2-decoupled: `llm` saiu. Entrou `ports` no canto superior esquerdo (A = 1, I = 0, sobre a Main Sequence), e é para ele que as quatro features apontam agora. O único concreto que fala com o mundo externo é `adapters.gateway`, no meio do gráfico (I 0,50) e com Ca 1 (só `main`). `config` continua no mesmo ponto, mas mudou de papel: Ca caiu de 6 para 1 e não tem mais provider, modelo nem chave. O D das features subiu de 0,20-0,25 para 0,33 porque elas passaram a importar menos coisas (Ce 3 → 2); por isso o critério de pronto é zona de dor mais direção das dependências (ADR 0009).
- main: os modos de execução trouxeram `jobs` (tarefas da F3, fora da zona) e `errors` (exceções do domínio, que tiraram o `HTTPException` das features). As features voltaram a I 0,67-0,75 porque importam `errors`, que é estável. `main` concentra os concretos (I = 1, Ce 10), como ponto de composição.

Exceções declaradas no ADR 0009 (estáveis por natureza, na zona de dor só pela fórmula): `schemas` (tipos pydantic do contrato), `errors` (exceções sem lógica) e `config` (só leitura de ambiente, Ca 1). O componente que chama o gateway e as features estão fora da zona.

## Tabela de capacidades

A aplicação conhece só a coluna "Capacidade lógica". O resto está em `gateway/config.yaml`.

| Capacidade lógica | Feature | Modelo primário | Fallback técnico | Modelo fraco | Máx. de tentativas por destino |
|---|---|---|---|---|---|
| `ticket-classification` | F1 | `openai/gpt-fake-large` | `anthropic/claude-fake-large` | `openai/gpt-fake-mini` (aceito) | 2 por destino em `5xx`/`429`; 1 em timeout (4 s por destino) |
| `reply-suggestion` | F2 | `anthropic/claude-fake-large` | `openai/gpt-fake-large` | `anthropic/claude-fake-mini` (aceito) | 2 por destino em `5xx`/`429`; 1 em timeout (4 s até o primeiro trecho) |
| `topics-report` | F3 | `anthropic/claude-fake-large` | `openai/gpt-fake-large` | `anthropic/claude-fake-mini` (aceito) | 2 por destino em `5xx`/`429`; 1 em timeout (20 s por lote); valores por lote |
| `order-extraction` | F4 | `openai/gpt-fake-large` | `anthropic/claude-fake-large` | nenhum (recusado) | 2 por destino em `5xx`/`429`; 1 em timeout (4 s por destino) |

Por chamada da aplicação: no máximo 2 tentativas no primário, 2 no fallback técnico e 2 no modelo fraco (onde existe). O retry com backoff exponencial é do LiteLLM (`router_settings.num_retries: 1` + `retry_policy`). O SDK da aplicação usa `max_retries=0`, para que os retries não se multipliquem. Timeout total na aplicação: 12 s para F1, F4 e cada trecho da F2; 50 s por lote e 55 s de prazo total na F3. Detalhes no ADR 0005.

## Tabela de fallback

O que acontece quando não há nenhum modelo `large` disponível (os dois `large` em `error_500`):

| Feature | Resposta | Status | Por quê (ADR 0005) |
|---|---|---|---|
| F1 Classificar | classificação feita pelo `gpt-fake-mini` | `200` | o `mini` classificou igual ao `large` em 200 de 200 tickets |
| F2 Sugerir resposta | sugestão do `claude-fake-mini` em streaming, mais curta (~1.000 contra ~2.400 caracteres) | `200` + `event: end` | um atendente humano lê e edita antes de enviar; um rascunho menor ajuda mais que um erro |
| F3 Relatório | relatório produzido pelo `claude-fake-mini` | `202`, depois `303` e `200` com o relatório | saída de `topics` idêntica no lote medido; o relatório não alimenta decisão automática |
| F4 Extrair dados | erro explícito `{"detail": "Nenhum modelo disponível para a capacidade order-extraction no momento"}` | `503` | o `mini` errou o número do pedido em 31 de 200 tickets (pega a nota fiscal) e a saída alimenta troca automática sem revisão |

Outras falhas: recusa de orçamento ou limite do gateway vira `429` com o motivo (F1, F2, F4) ou `failed` com o motivo (F3); um erro no meio do stream da F2 vira `event: error`; uma F3 que não termina chega a `failed` em até 55 s.

Para reproduzir (os dois `large` em `error_500`):

```
curl -s -X POST localhost:8090/admin/reset
curl -s -X POST localhost:8090/admin/failures -H "Content-Type: application/json" -d '{"provider": "openai", "model": "gpt-fake-large", "mode": "error_500"}'
curl -s -X POST localhost:8090/admin/failures -H "Content-Type: application/json" -d '{"provider": "anthropic", "model": "claude-fake-large", "mode": "error_500"}'
# chame as 4 features (seção Fluxos) e confira em seguida:
curl -s "localhost:8090/admin/calls?last=50"
```

Fallback técnico (primário em `error_500`):

```
curl -s -X POST localhost:8090/admin/reset
curl -s -X POST localhost:8090/admin/failures -H "Content-Type: application/json" -d '{"provider": "openai", "mode": "error_500"}'
curl -s -X POST localhost:8000/tickets/classification -H "Content-Type: application/json" \
  -d '{"ticket_id": "TK-00042", "text": "Meu pedido #481516 não chegou e já passou do prazo, urgente"}'
curl -s "localhost:8090/admin/calls?last=5"
# gpt-fake-large 500, gpt-fake-large 500, claude-fake-large 200
```

Para voltar ao modo normal: `curl -s -X POST localhost:8090/admin/reset`.

## Fluxos

Decisões no ADR 0004 (uma seção por feature, com a árvore de decisão).

### F1 Classificar ticket: síncrono, com timeout explícito

```
curl -s -X POST localhost:8000/tickets/classification -H "Content-Type: application/json" \
  -d '{"ticket_id": "TK-00042", "text": "Meu pedido #481516 não chegou e já passou do prazo, urgente"}'
```

`200 {"ticket_id": "TK-00042", "category": "delivery", "priority": "high"}` em ~1,1 s. Com o primário travado (`timeout`), responde via fallback em ~5 s; se toda a cadeia travar, `503` explícito em até 12 s.

### F2 Sugerir resposta: streaming (SSE)

```
curl -N -X POST localhost:8000/tickets/reply-suggestion -H "Content-Type: application/json" \
  -d '{"ticket_id": "TK-00042", "text": "Meu pedido #481516 não chegou e já passou do prazo, urgente"}'
```

`200`, `Content-Type: text/event-stream`. O primeiro trecho chega em < 1 s e o texto continua chegando até ~16 s:

```
data: {"chunk": "Olá!"}
data: {"chunk": " Sin"}
...
event: end
data: {"ticket_id": "TK-00042"}
```

Falha no meio do stream (o `200` já foi enviado): `event: error` com `data: {"ticket_id": "TK-00042", "message": "A geração foi interrompida"}` e o stream termina. Se nenhum destino responder antes do primeiro trecho, o cliente recebe `503` (ou `429`) com JSON em vez de um stream vazio. A resposta leva `X-Accel-Buffering: no`, que desliga o buffer da borda só para ela.

### F3 Relatório de temas: assíncrono (Asynchronous Request-Reply)

```
curl -s -i -X POST localhost:8000/reports/topics -H "Content-Type: application/json" \
  -d '{"start": "2026-08-01", "end": "2026-08-31"}'
# 202 Accepted, Location: /reports/topics/status/<id>, Retry-After: 5
# corpo: {"id": "<id>", "state": "pending", "status_url": "/reports/topics/status/<id>"}

curl -s -i localhost:8000/reports/topics/status/<id>
# enquanto roda: 200 {"state": "running", "progress": "1800/5000"} (+ Retry-After: 5)
# se falhar:     200 {"state": "failed", "progress": "...", "reason": "<motivo>"}
# quando termina: 303 See Other, Location: /reports/topics/<id>

curl -s localhost:8000/reports/topics/<id>
# 200 {"start": "2026-08-01", "end": "2026-08-31", "total_tickets": 5000, "topics": [...]}
```

Ou, seguindo o redirecionamento: `curl -s -L localhost:8000/reports/topics/status/<id>`. O `POST` responde em milissegundos; o mês completo fica pronto em cerca de 30 a 35 s (34 lotes, até 12 em paralelo). Erros de entrada continuam síncronos (`422`). `GET` de um id desconhecido responde `404`. Campos adicionais em relação aos Contratos sugeridos: `id` e `status_url` no corpo do `202` e `reason` no estado `failed`.

### F4 Extrair dados do pedido: síncrono, com timeout explícito

```
curl -s -X POST localhost:8000/tickets/extraction -H "Content-Type: application/json" \
  -d '{"ticket_id": "TK-04171", "text": "Tenho aqui a nota fiscal 702732. Fiz o pix de o smartwatch e o pagamento consta como pendente. Referente ao pedido #364733. Prefiro contato por e-mail."}'
```

`200 {"ticket_id": "TK-04171", "order_number": "#364733", "product": "smartwatch"}` em ~1,1 s. Sem nenhum `large`, `503` explícito (sem modelo fraco).

## Troca de modelo

Arquivo: `gateway/config.yaml`. Em `model_list`, cada capacidade tem uma entrada com o destino primário. Para trocar o modelo físico, altere a âncora (`*openai-large`, `*openai-mini`, `*anthropic-large`, `*anthropic-mini`) do `litellm_params` da capacidade. Exemplo, F1 para o modelo barato:

```diff
   - model_name: ticket-classification
-    litellm_params: {<<: *openai-large, timeout: 4}
+    litellm_params: {<<: *openai-mini, timeout: 4}
```

Comando (reinicia só o gateway; a aplicação não é reconstruída nem reiniciada):

```
docker compose restart gateway
until docker compose ps gateway | grep -q healthy; do sleep 1; done
curl -s -X POST localhost:8000/tickets/classification -H "Content-Type: application/json" \
  -d '{"ticket_id": "TK-00042", "text": "Meu pedido #481516 não chegou e já passou do prazo, urgente"}'
curl -s "localhost:8090/admin/calls?last=1"     # model: gpt-fake-mini
docker compose ps app                          # app continua "Up" desde antes da troca
```

Resultado medido: depois do restart do gateway (~20 s até ficar saudável), a chamada seguinte apareceu em `/admin/calls` como `openai gpt-fake-mini classify 200`, e o `StartedAt` do container `app` não mudou. Para voltar, desfaça a alteração e reinicie o gateway de novo.

O mesmo vale para trocar de provider (ex.: `*anthropic-large` na F1), mudar o fallback técnico (entradas `<capacidade>-fallback`) ou ligar e desligar o modelo fraco (lista `router_settings.fallbacks`).

## Roteiro de governança

Duas chaves virtuais, criadas no boot a partir de `gateway/keys.json` (ADR 0006):

| Chave | Features | Orçamento | Limite |
|---|---|---|---|
| `helpdesk-realtime` (`GATEWAY_REALTIME_KEY`) | F1, F2, F4 | US$ 30 / 30 dias | 120 req/min |
| `helpdesk-reports` (`GATEWAY_REPORTS_KEY`) | F3 | US$ 20 / 30 dias | 120 req/min |

O roteiro aperta os limites pela API de administração do gateway, com a master key, e confere que as recusas não chegam ao provider. Rode desta pasta, com o `.env` criado:

```
set -a; . ./.env; set +a
calls() { curl -s "localhost:8090/admin/calls?last=5000" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))"; }
T='{"ticket_id": "TK-00042", "text": "Meu pedido #481516 não chegou e já passou do prazo, urgente"}'
```

1) Recusa por orçamento (F3): orçamento da chave de relatórios zerado.

```
curl -s localhost:4000/key/update -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" \
  -d "{\"key\": \"$GATEWAY_REPORTS_KEY\", \"max_budget\": 0}"
calls                                                     # ex.: 2
curl -s -i -X POST localhost:8000/reports/topics -H "Content-Type: application/json" \
  -d '{"start": "2026-08-01", "end": "2026-08-31"}'       # 202 + Location
curl -s localhost:8000/reports/topics/status/<id>
# {"state":"failed","progress":"0/5000","reason":"O gateway recusou a capacidade topics-report: orçamento esgotado"}
calls                                                     # continua 2
```

2) Recusa por limite de requisições (F1): 1 requisição por minuto na chave de tempo real.

```
curl -s localhost:4000/key/update -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" \
  -d "{\"key\": \"$GATEWAY_REALTIME_KEY\", \"rpm_limit\": 1}"
calls                                                     # ex.: 2
for i in 1 2 3; do curl -s -w " %{http_code}\n" -X POST localhost:8000/tickets/classification -H "Content-Type: application/json" -d "$T"; done
# {"ticket_id":"TK-00042","category":"delivery","priority":"high"} 200
# {"detail":"O gateway recusou a capacidade ticket-classification: limite de requisições esgotado"} 429
# {"detail":"O gateway recusou a capacidade ticket-classification: limite de requisições esgotado"} 429
calls                                                     # 3: só a requisição aceita chegou ao provider
```

Se a chave de tempo real foi usada no último minuto, a primeira requisição também pode ser recusada. O que vale é que `calls` só aumenta com as requisições aceitas.

3) Restaurar os valores de `gateway/keys.json` (ou `docker compose restart gateway`, que reaplica o arquivo):

```
curl -s localhost:4000/key/update -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" \
  -d "{\"key\": \"$GATEWAY_REPORTS_KEY\", \"max_budget\": 20}"
curl -s localhost:4000/key/update -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" \
  -d "{\"key\": \"$GATEWAY_REALTIME_KEY\", \"rpm_limit\": 120}"
```

O gasto acumulado de cada chave aparece em `curl -s "localhost:4000/key/info?key=$GATEWAY_REPORTS_KEY" -H "Authorization: Bearer $LITELLM_MASTER_KEY"`. O custo usa os preços por token do provider declarados em `gateway/config.yaml`.

## Mapa de decisões

| ADR | Nível | Resumo |
|---|---|---|
| [0001](docs/adr/0001-providers-aceitos-e-teto-de-gasto.md) | corporativa | Só OpenAI e Anthropic, sempre via gateway da empresa, com teto de US$ 50/mês para a IA do helpdesk (30 tempo real + 20 relatórios). |
| [0002](docs/adr/0002-ai-gateway-litellm.md) | solução | LiteLLM Proxy self-hosted como serviço `gateway`, único lugar com credenciais e modelos físicos; limitações da ferramenta e como foram tratadas. |
| [0003](docs/adr/0003-capacidades-logicas.md) | solução | Uma capacidade lógica por feature; primário mantém o provider da v1, fallback técnico no outro provider, modelo fraco por feature. |
| [0004](docs/adr/0004-modo-de-execucao-por-feature.md) | solução | Modo de execução: F1 e F4 síncronas com timeout, F2 streaming SSE, F3 Asynchronous Request-Reply em memória. |
| [0005](docs/adr/0005-resiliencia-e-fallback.md) | solução | Timeout, retry (2 tentativas por destino) e fallback no gateway; modelo fraco aceito em F1, F2, F3 e recusado na F4, com a evidência medida. |
| [0006](docs/adr/0006-governanca-chaves-orcamento-limites.md) | solução | Uma chave virtual por perfil de carga (tempo real e relatórios), cada uma com orçamento, limite de requisições e só as próprias capacidades. |
| [0007](docs/adr/0007-banco-do-gateway.md) | software | Serviço `gateway-db` (Postgres) para chaves e orçamentos, e provisionamento das chaves no boot do gateway, sem passo manual. |
| [0008](docs/adr/0008-portas-e-adaptador-unico-do-gateway.md) | software | Features dependem de portas (`TextModel`, `TicketSource`); um único adaptador fala com o gateway, montado em `main.py`. |
| [0009](docs/adr/0009-leitura-da-metrica.md) | software | Leitura da métrica: critério de pronto por zona de dor e direção das dependências; `schemas`, `errors` e `config` estáveis por natureza. |

O plano de refatoração, com o piloto, as revisões e o handoff para o agente de IA, está em [`docs/refactoring-plan.md`](docs/refactoring-plan.md).

Marcos no git: tags `v1-coupled` (aplicação recebida mais a suíte de caracterização) e `v2-decoupled` (aplicação refatorada atrás do gateway, mesmo comportamento); a versão final está na branch `main`.
