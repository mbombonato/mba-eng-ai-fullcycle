# A Ponte: um agente A2A com MCP por dentro

Entrega do desafio do módulo **Desenvolvimento de Agentes com IA** (MBA Engenharia de Software com IA, Full Cycle).
O enunciado está em [`ENUNCIADO.md`](ENUNCIADO.md).

São dois processos Python separados: um servidor MCP com as tools de sala e um agente que é servidor A2A por fora e host MCP por dentro.
O agente não usa LLM: interpreta o pedido em formato fixo e decide por regra.

| Processo | Pasta | Porta | Endpoint |
|---|---|---|---|
| Servidor MCP | `servidor-mcp/` | `7301` | `POST /mcp` (Streamable HTTP stateless, revisão `2026-07-28`) |
| Agente | `agente/` | `7300` | `POST /a2a` (A2A v1.0, JSON-RPC 2.0) e `GET /.well-known/agent-card.json` |

O servidor MCP expõe `listar_salas`, `consultar_disponibilidade`, `reservar_sala` e o resource `politica://uso`.

Versões travadas em `pyproject.toml` e `uv.lock` de cada processo, espelhadas em `requirements.txt`:
`mcp==2.3.0`, `uvicorn==0.54.0`, `starlette==1.10.0`, `httpx==0.28.1`.

## Como rodar

Pré-requisitos:

- Python 3.11 ou superior para os dois processos. O validador roda com Python 3.10+, sem dependências.
- [uv](https://docs.astral.sh/uv/), que baixa o interpretador certo se preciso. Há uma alternativa com `pip` abaixo.

Todos os comandos partem da pasta do desafio, `06-agente-a2a-com-mcp`.

### 1. Clonar e gerar a chave do `requestState` (uma vez)

```bash
git clone https://github.com/mbombonato/mba-eng-ai-fullcycle.git
cd mba-eng-ai-fullcycle/06-agente-a2a-com-mcp
echo "REQUEST_STATE_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" > .env
```

O servidor MCP lê `REQUEST_STATE_SECRET` do ambiente e, se ela não estiver exportada, do `.env` desta pasta (que está no `.gitignore`).
Também funciona exportar no terminal do servidor:

```bash
export REQUEST_STATE_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

Sem a variável, ou com menos de 32 bytes, o servidor não sobe.

### 2. Terminal 1: servidor MCP

```bash
cd servidor-mcp
uv run python3 servidor.py
```

O stderr deste terminal é o log de requests.

### 3. Terminal 2: agente

```bash
cd agente
uv run python3 agente.py
```

### 4. Terminal 3: validador

Na pasta do desafio, com os dois processos recém-iniciados:

```bash
python3 validador/validar.py --agente http://localhost:7300 --mcp http://localhost:7301
```

### Resultado esperado

O validador imprime o trace-id da execução, 36 linhas `PASS` e termina com
`resumo: 36 passaram, 0 falharam, de 36 verificacoes` e código de saída 0.
A saída completa está em [Saída do validador](#saída-do-validador).

### Limitações

- As reservas ficam em memória. Reinicie os dois processos (Ctrl+C e o mesmo comando) antes de rodar o validador de novo e antes dos passos 7 a 13 do fluxo do avaliador, porque as reservas criadas mudam as alternativas oferecidas.
- O `requestState` vale 10 minutos. No passo 12 do fluxo do avaliador, o retry precisa chegar dentro desse prazo e o servidor precisa subir com a mesma chave (com o `.env`, isso já acontece).

### Alternativa sem uv

Um venv por processo, cada linha em um terminal, a partir da pasta do desafio:

```bash
cd servidor-mcp && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python servidor.py
cd agente      && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python agente.py
```

### Variáveis opcionais

Os padrões já são os que o validador espera. A lista também está em `.env.example`.

| Variável | Padrão | Uso |
|---|---|---|
| `MCP_HOST` | `127.0.0.1` | host do servidor MCP |
| `MCP_PORT` | `7301` | porta do servidor MCP |
| `AGENTE_HOST` | `127.0.0.1` | host do agente |
| `AGENTE_PORT` | `7300` | porta do agente |
| `AGENTE_URL_PUBLICA` | `http://127.0.0.1:7300` | URL publicada no card |
| `MCP_URL` | `http://127.0.0.1:7301/mcp` | endereço do servidor MCP usado pelo agente |
| `MCP_LOG_BODY` | desligado | com `1`, o servidor MCP loga também os headers `MCP-*` e o corpo de cada request |

## Atalhos para o fluxo do avaliador

Os números são os passos da seção "Fluxo do avaliador" do enunciado. Rode a partir da pasta do desafio.

```bash
# passo 3: o card
curl -s http://localhost:7300/.well-known/agent-card.json

# passo 7: sala ocupada -> TASK_STATE_INPUT_REQUIRED com "alternativas: sala-fusca, sala-mirante"
python3 -c "import json; print(json.dumps(json.load(open('exemplos/wire/08-a2a-send-message.json'))['request']['body']))" \
  | curl -s http://localhost:7300/a2a -H 'Content-Type: application/json' \
         -H 'traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01' -d @-

# passo 8: continuar (troque <task-id>) e conferir com GetTask
curl -s http://localhost:7300/a2a -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":2,"method":"SendMessage","params":{"message":{"messageId":"msg-1","role":"ROLE_USER","parts":[{"text":"escolha=sala-mirante"}],"taskId":"<task-id>"}}}'
curl -s http://localhost:7300/a2a -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":3,"method":"GetTask","params":{"id":"<task-id>"}}'
```

Passo 9: repita o comando do passo 7 e, no do passo 8, troque `escolha=sala-mirante` por `escolha=recusar`.

Passos 11 a 13: os corpos e headers dos requests diretos ao servidor MCP estão em `exemplos/wire/` (`03-tools-call-conflito-input-required.json`, `04-tools-call-retry.json` e `06-erro-32021-sem-elicitation.json`), nos campos `request.headers` e `request.body`.

Passos 5 e 6, no stderr do servidor MCP. Cada request aparece como:

```
recebido metodo=<método> id=<id> [alvo=<tool ou uri>] [retry=sim] traceparent=<valor>
respondido http=<status>
```

- Passo 5: procure o trace-id que o validador imprime na primeira linha. Ele aparece no `tools/list`, no `resources/read` e no `tools/call` do agente.
- Passo 6: o retry aparece com `retry=sim` e um id maior que o do `tools/call` inicial da mesma Task.

## Onde a ponte acontece

A ponte está em [`agente/agente.py`](agente/agente.py).

Ida: `concluir()` recebe o resultado do `tools/call`. Quando o `resultType` é `input_required`, chama `pausar_task()`, que guarda numa `PausaMcp` ([`agente/tarefas.py`](agente/tarefas.py)) a chave do `inputRequests`, os argumentos originais e o `requestState`, e põe a Task em `TASK_STATE_INPUT_REQUIRED` com a linha `alternativas: <ids na ordem do enum>`.

Volta: `retomar_task()`, chamada pelo `SendMessage` de continuação, repete o `tools/call` original via `ClienteMcp.chamar_tool()` ([`agente/cliente_mcp.py`](agente/cliente_mcp.py)) com id JSON-RPC novo, `inputResponses` na mesma chave e o `requestState` ecoado sem alteração. O resultado volta para `concluir()`, que fecha a Task ou pausa de novo.

No servidor ([`servidor-mcp/servidor.py`](servidor-mcp/servidor.py)), a pergunta nasce em `pedir_escolha()` e o retry é tratado em `reservar_sala()`.

## Decisões técnicas

### Como o `requestState` é protegido

Com o utilitário do SDK: `RequestStateSecurity(keys=[chave], ttl=600, audience="central-de-salas")`.
O estado (pedido original e alternativas oferecidas) é selado com AES-256-GCM, com chave derivada por HKDF-SHA256 de `REQUEST_STATE_SECRET`. O envelope inclui emissão, expiração, método, nome da tool, digest SHA-256 dos argumentos e audiência.

- `requestState` adulterado: `-32602` com HTTP 400, antes de chegar à tool.
- Argumentos adulterados no retry: `-32602`, porque o digest selado não bate. A tool também reconstrói o pedido a partir do estado selado, não dos argumentos reenviados.
- A chave vem só de `REQUEST_STATE_SECRET` (ambiente ou `.env` local), tem no mínimo 32 bytes e não tem valor padrão no código.

### Por quanto tempo ele vale

10 minutos (`ttl=600`). Expirado, a resposta é `-32602`.

### Onde fica o estado das Tasks

Em memória no processo do agente: `RepositorioDeTasks`, em `agente/tarefas.py`, um dicionário `task_id -> Task`.
A Task pública e a pausa MCP (`PausaMcp`, que contém o `requestState`) são objetos separados, e só a Task pública é serializada. Por isso o `requestState` não aparece no card, em artifact, em mensagem nem no `GetTask`.
Cada Task tem a sua própria pausa e um `asyncio.Lock`.
`SendMessage` para Task em estado terminal recebe o erro `-32004`; para Task inexistente, `-32001`.

### O servidor não guarda nada entre as rodadas

O pedido original e as alternativas viajam no `requestState`, então o retry funciona depois de reiniciar o servidor MCP.
A tool devolve `InputRequiredResult` e lê `ctx.request_state` e `ctx.input_responses` diretamente, em vez de usar `Resolve(...)`/`Elicit` do SDK.
Se a sala escolhida tiver sido ocupada entre as rodadas, o servidor faz uma pergunta nova com as alternativas atuais.

### `traceparent`

O agente lê o header `traceparent` do request A2A e envia, no `_meta` de cada request MCP daquela Task, um `traceparent` com o mesmo trace-id e span-id novo.
Na continuação vale o header do request de continuação ou, se ele não vier, o trace-id guardado na Task. Sem header, a Task ganha um trace-id próprio.

### Limitação do SDK: o agente não usa o `Client` de alto nível

O `Client` do SDK resolve o MRTR sozinho: com um `elicitation_callback`, o ciclo fecha sem voltar ao cliente A2A. Ele também declara a capability como `form` + `url`, sem opção de restringir. Evidência, em `mcp/client/session.py` (`mcp==2.3.0`):

```python
elicitation = (
    types.ElicitationCapability(form=types.FormElicitationCapability(), url=types.UrlElicitationCapability())
    if self._elicitation_callback is not _default_elicitation_callback
    else None
)
```

Por isso `agente/cliente_mcp.py` é um cliente JSON-RPC sobre HTTP que valida as respostas com os tipos do SDK (`ListToolsResult`, `ReadResourceResult`, `CallToolResult`, `InputRequiredResult`) e entrega o `input_required` cru para a ponte. Ele aceita resposta JSON ou SSE.

## Saída do validador

Saída do validador com os dois processos recém-iniciados:

```
trace-id desta execucao: d0d380f31012d0e378ae8b813d25173a
procure esse valor no stderr do servidor MCP para conferir a propagacao do traceparent.

PASS 01 tools/list traz as tres tools
PASS 02 toda tool tem inputSchema de objeto
PASS 03 listar_salas devolve structuredContent e o mesmo JSON em texto
PASS 04 _meta sem protocolVersion devolve -32602 e HTTP 400
PASS 05 _meta sem clientCapabilities devolve -32602 e HTTP 400
PASS 06 tool inexistente e recusada, por -32602 ou por isError
PASS 07 resources/read de politica://uso devolve a politica
PASS 08 resources/read de URI inexistente devolve -32602
PASS 09 sala inexistente devolve isError com a mensagem exata
PASS 10 fora da janela devolve isError com a mensagem exata
PASS 11 duracao acima de 2h devolve isError com a mensagem exata
PASS 12 intervalo invertido devolve isError com a mensagem exata
PASS 13 conflito devolve input_required com inputRequests e requestState
PASS 14 a elicitation e form mode e oferece as alternativas na ordem certa
PASS 15 conflito sem a capability elicitation devolve -32021 e HTTP 400
PASS 16 retry com inputResponses e requestState conclui a reserva
PASS 17 requestState adulterado e rejeitado com -32602
PASS 18 argumentos adulterados no retry nao tomam efeito
PASS 19 recusa conclui sem reservar e sem isError
PASS 20 conflito sem alternativa possivel devolve isError com a mensagem exata

PASS 21 agent card responde 200 no well-known com JSON
PASS 22 o card declara a interface JSON-RPC com url e versao 1.0
PASS 23 o card declara a skill reservar-sala
PASS 24 SendMessage com sala livre conclui a Task
PASS 25 o artifact chama reserva e traz a versao da politica
PASS 26 GetTask devolve id, contextId e estado corrente
PASS 27 SendMessage com sala ocupada pausa a Task
PASS 28 a Task pausada lista as alternativas na ordem certa
PASS 29 escolha fora do enum mantem a Task pausada
PASS 30 a continuacao conclui a Task na sala escolhida
PASS 31 SendMessage em Task terminal e recusado
PASS 32 a recusa termina a Task em CANCELED
PASS 33 duas Tasks pausadas ao mesmo tempo concluem cada uma com a sua reserva
PASS 34 nenhuma resposta A2A carrega o requestState
PASS 35 sala inexistente termina a Task em FAILED com a mensagem da tool
PASS 36 o agente e deterministico: o mesmo pedido produz a mesma pausa

resumo: 36 passaram, 0 falharam, de 36 verificacoes
```
