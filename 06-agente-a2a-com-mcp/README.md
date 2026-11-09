# A Ponte: um agente A2A com MCP por dentro

Entrega do desafio do módulo **Desenvolvimento de Agentes com IA** (MBA Engenharia de Software com IA, Full Cycle).
O enunciado completo está em [`ENUNCIADO.md`](ENUNCIADO.md).

São dois processos separados, em Python:

| Processo | Pasta | Porta | Endpoint | Papel |
|---|---|---|---|---|
| Servidor MCP | `servidor-mcp/` | `7301` | `POST /mcp` (Streamable HTTP, stateless, revisão `2026-07-28`) | expõe `listar_salas`, `consultar_disponibilidade`, `reservar_sala` e o resource `politica://uso` |
| Agente | `agente/` | `7300` | `POST /a2a` (A2A v1.0, JSON-RPC 2.0) e `GET /.well-known/agent-card.json` | servidor A2A por fora, host/cliente MCP por dentro |

Stack (versões travadas em `pyproject.toml` + `uv.lock`, e espelhadas em `requirements.txt`):
`mcp==2.3.0` (SDK oficial v2, alinhado à spec `2026-07-28`), `uvicorn==0.54.0`, `starlette==1.10.0`, `httpx==0.28.1`.
Nenhum SDK de LLM: o agente interpreta um pedido em formato fixo e decide por regra.

---

## Como rodar

Pré-requisitos: Python 3.11 ou superior e [uv](https://docs.astral.sh/uv/) (há uma alternativa com `pip` logo abaixo).
O validador roda com o `python3` do sistema (3.10+), sem dependências.

**1. Clonar e gerar a chave de integridade do `requestState`** (uma vez):

```bash
git clone <url-do-seu-fork> desafio-a2a-com-mcp
cd desafio-a2a-com-mcp
echo "REQUEST_STATE_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" > .env
```

O servidor MCP lê `REQUEST_STATE_SECRET` do ambiente; se ela não estiver exportada, lê o `.env` da raiz
(que está no `.gitignore`). Também funciona exportando direto no terminal do servidor:
`export REQUEST_STATE_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")`.
Sem a variável, ou com menos de 32 bytes, o servidor se recusa a subir. Nunca versione o valor.

**2. Terminal 1, servidor MCP** (o stderr dele é o log de requests):

```bash
cd servidor-mcp
uv run python servidor.py
```

**3. Terminal 2, agente:**

```bash
cd agente
uv run python agente.py
```

**4. Terminal 3, validador** (com os dois processos recém-iniciados):

```bash
python3 validador/validar.py --agente http://localhost:7300 --mcp http://localhost:7301
```

As reservas ficam em memória. Para rodar o validador de novo, ou para seguir os passos 7 a 13 do
"Fluxo do avaliador" depois dele, reinicie os dois processos (Ctrl+C e o mesmo comando), porque as reservas
que o validador cria mudam as alternativas oferecidas.

**Alternativa sem uv** (um venv por processo):

```bash
cd servidor-mcp && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python servidor.py
cd agente      && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python agente.py
```

**Variáveis opcionais** (os padrões já são os exigidos): `MCP_HOST`, `MCP_PORT` (7301), `AGENTE_HOST`, `AGENTE_PORT` (7300),
`AGENTE_URL_PUBLICA` (URL publicada no card, padrão `http://127.0.0.1:7300`), `MCP_URL` (padrão `http://127.0.0.1:7301/mcp`)
e `MCP_LOG_BODY=1`, que faz o servidor MCP logar também os headers `MCP-*` e o corpo de cada request. Veja `.env.example`.

### Atalhos para o fluxo do avaliador

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

No stderr do servidor MCP, cada request aparece como
`recebido metodo=<método> id=<id> [alvo=<tool ou uri>] [retry=sim] traceparent=<valor>` seguido de `respondido http=<status>`.
Para o passo 5, procure o trace-id que o validador imprime na primeira linha: ele aparece no `tools/list`, no
`resources/read` e no `tools/call` do agente. Para o passo 6, o retry aparece com `retry=sim` e um id maior que o do
`tools/call` inicial da mesma Task (o agente nunca repete id).

---

## Onde a ponte acontece

Tudo está em [`agente/agente.py`](agente/agente.py). A ida é `concluir()` (linha ~210), que recebe o resultado cru do
`tools/call` (o cliente MCP do agente, [`agente/cliente_mcp.py`](agente/cliente_mcp.py), devolve `InputRequiredResult` sem
tentar resolvê-lo) e, quando o `resultType` é `input_required`, chama `pausar_task()` (linha ~143). É ali que o
`input_required` do MCP vira `TASK_STATE_INPUT_REQUIRED`: a função lê a única entrada de `inputRequests`, pega o `enum`
(ou `const`) da propriedade do `requestedSchema`, guarda numa `PausaMcp` ([`agente/tarefas.py`](agente/tarefas.py)) a
chave da entrada, o nome da tool, os argumentos originais e o `requestState` intocado, e transita a Task com a mensagem
`alternativas: <ids na ordem do enum>`. A volta é `retomar_task()` (linha ~183), chamada pelo `SendMessage` de
continuação (`send_message()`, com `taskId` e `escolha=<valor>`) depois de conferir que a escolha está no `enum`
(senão a Task continua pausada e repete as alternativas). Ela monta `inputResponses` com a mesma chave
(`accept` + `{"sala": <escolha>}` ou `decline` para `escolha=recusar`), põe a Task em `WORKING` e repete o `tools/call`
original pelo `ClienteMcp.chamar_tool()`, que sempre sai com um id JSON-RPC novo (contador monotônico em
`cliente_mcp.py`) e leva o `requestState` ecoado byte a byte. O resultado volta para `concluir()`, que fecha a Task em
`COMPLETED` (com o artifact `reserva`), `CANCELED` (recusa) ou `FAILED` (erro de execução da tool, com a mensagem exata no
histórico), ou pausa de novo se o servidor fizer outra pergunta.

Do lado do servidor, a pergunta nasce em `pedir_escolha()` e o retry é tratado no próprio `reservar_sala()`
([`servidor-mcp/servidor.py`](servidor-mcp/servidor.py)).

---

## Decisões técnicas

**Proteção do `requestState`.** Uso o utilitário do SDK: `MCPServer(..., request_state_security=RequestStateSecurity(keys=[chave], ttl=600, audience="central-de-salas"))`.
A tool devolve o estado em texto puro (`{"v":1,"pedido":{sala,inicio,fim,responsavel},"opcoes":[...]}`) e a
`RequestStateBoundary` do SDK o envolve num envelope com `iat`, `exp`, método, nome da tool, digest SHA-256 dos
argumentos e audiência, e sela com **AES-256-GCM** (chave derivada por HKDF-SHA256 de `REQUEST_STATE_SECRET`). Então é
cifrado e autenticado: trocar um caractere quebra a tag GCM e o request é recusado com `-32602`
(`Invalid or expired requestState`, HTTP 400) antes de chegar à tool. Argumentos adulterados no retry também são
recusados com `-32602`, porque o digest dos argumentos selado não bate; e, mesmo que batesse, a tool reconstrói o pedido
a partir do estado selado, não dos argumentos reenviados. A chave vem só do ambiente (ou do `.env` local, fora do git),
precisa ter no mínimo 32 bytes (64 caracteres hex) e não existe valor padrão no código.

**Validade.** 10 minutos (`ttl=600`), dentro da faixa de 5 a 30 pedida. Expirado, a resposta é `-32602`.

**Nada guardado no servidor entre as rodadas.** O servidor não lembra de nada entre o `input_required` e o retry: o pedido
original e as alternativas oferecidas viajam no `requestState`. Por isso um retry apresentado depois de reiniciar o
servidor MCP funciona (testado no passo 12 do fluxo do avaliador). Optei pelo fluxo explícito (a tool devolve
`InputRequiredResult` e lê `ctx.request_state`/`ctx.input_responses`) em vez do padrão `Resolve(...)`/`Elicit` do SDK,
porque o `Resolve` recalcula a pergunta a cada rodada e só aceita a resposta se o `enum` for idêntico. Depois de um
restart as reservas em memória voltam ao seed, o `enum` pode mudar, e o retry seria perguntado de novo em vez de
concluir. Se a sala escolhida tiver sido ocupada entre as rodadas, o servidor faz uma pergunta nova com as alternativas
atuais.

**Capability e `-32021`.** O servidor só pergunta para quem declarou elicitation em form mode no `_meta` daquele
request (`{"elicitation": {}}` sem modos conta como form, como diz a spec). Sem isso, devolve `-32021` com
`data.requiredCapabilities = {"elicitation": {"form": {}}}` e o transporte do SDK responde HTTP 400. A checagem de
`_meta` obrigatório (`-32602`/HTTP 400) e de headers espelhados (`-32020`) é do próprio SDK, sem inferir nada de request
anterior (modo `stateless_http=True`).

**Estado das Tasks.** Em memória no processo do agente (`RepositorioDeTasks` em `agente/tarefas.py`), um dicionário
`task_id -> Task`. A Task pública (id, contextId, status, history, artifacts) e a pausa MCP (`PausaMcp`, que contém o
`requestState`) são objetos separados, e só a primeira é serializada para o wire. Assim o `requestState` nunca aparece em
card, artifact, mensagem ou `GetTask`. Cada Task tem a sua pausa e um `asyncio.Lock`, então duas Tasks pausadas ao mesmo
tempo nunca trocam de `requestState`, e duas continuações simultâneas da mesma Task não disparam dois retries. Estado
terminal é definitivo: `SendMessage` para Task `COMPLETED`/`CANCELED`/`FAILED` recebe erro JSON-RPC `-32004`
(UnsupportedOperationError), e para Task inexistente `-32001` (TaskNotFoundError).

**Agente como host MCP.** A cada Task o agente faz `tools/list` (confere que `reservar_sala` existe e monta os argumentos a
partir do `inputSchema` descoberto), `resources/read` de `politica://uso` (extrai a versão da primeira linha, que vai no
campo `politica` do artifact) e só então `tools/call`. Todo request leva no `_meta` `protocolVersion`, `clientInfo`,
`clientCapabilities = {"elicitation": {"form": {}}}` e `traceparent`, e nos headers `MCP-Protocol-Version`, `Mcp-Method` e,
em `tools/call`/`resources/read`, `Mcp-Name`.

**`traceparent`.** O agente lê o header `traceparent` do request A2A e, em cada request MCP daquela Task, envia no `_meta`
um `traceparent` com o mesmo trace-id e um span-id novo. Na continuação vale o header do request de continuação ou, se
ele não vier, o trace-id guardado na Task. Sem header, a Task ganha um trace-id próprio.

**Por que o agente não usa o `Client` de alto nível do SDK.** Ele resolve o MRTR sozinho: com um
`elicitation_callback` o ciclo fecha sem voltar ao cliente A2A, que é justamente o que o enunciado proíbe. Além disso,
ele declara a capability como `form` + `url`, sem opção de restringir. Evidência, em
`mcp/client/session.py` (`mcp==2.3.0`):

```python
elicitation = (
    types.ElicitationCapability(form=types.FormElicitationCapability(), url=types.UrlElicitationCapability())
    if self._elicitation_callback is not _default_elicitation_callback
    else None
)
```

Por isso o cliente MCP do agente (`agente/cliente_mcp.py`) é um cliente JSON-RPC sobre HTTP pequeno, que valida as
respostas com os tipos do SDK oficial (`mcp_types.ListToolsResult`, `ReadResourceResult`, `CallToolResult`,
`InputRequiredResult`) e entrega o `input_required` cru para a ponte. Ele aceita resposta JSON ou SSE.

**Servidor A2A.** Implementado direto sobre Starlette, sem SDK de A2A: só há dois métodos (`SendMessage`, `GetTask`) no
binding JSON-RPC, e o card segue exatamente a forma v1.0 de `exemplos/wire/07-a2a-agent-card.json`
(`supportedInterfaces[]` com `protocolBinding: "JSONRPC"` e `protocolVersion: "1.0"`). A Task passa por `SUBMITTED` →
`WORKING` → (`INPUT_REQUIRED` ↔ `WORKING`) → `COMPLETED`/`CANCELED`/`FAILED`. O `SendMessage` é síncrono e devolve a Task
no estado em que a rodada parou; `GetTask` reflete o estado corrente a qualquer momento.

**Regras de negócio** ficam só no servidor MCP: validações na ordem sala → intervalo → janela (08:00–20:00 em -03:00,
início e fim) → duração (até 2 h); conflito por sobreposição; alternativas = salas livres no intervalo com capacidade
≥ à pedida, até 3, ordenadas por (capacidade, id). O agente só traduz protocolo.

**Logs.** O servidor MCP registra no stderr cada request na borda ASGI, antes do SDK, para que também apareçam os que o
SDK recusa (sem `_meta`, capability ausente, `requestState` inválido). O agente também loga no stderr os requests A2A
recebidos e os requests MCP emitidos (sem nunca imprimir o `requestState`, só o tamanho).

---

## Saída do validador

Última execução, com os dois processos recém-iniciados a partir de uma cópia limpa seguindo este README:

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
