"""Agente A2A da Central de Salas, com MCP por dentro.

- Por fora: servidor A2A v1.0, binding JSON-RPC 2.0, em http://127.0.0.1:7300/a2a,
  com o Agent Card em /.well-known/agent-card.json. Metodos: SendMessage e GetTask.
- Por dentro: host MCP que descobre as tools por `tools/list`, le o resource
  `politica://uso` e chama `reservar_sala` no servidor MCP, por HTTP.
- No meio, a ponte: `input_required` do MCP vira `TASK_STATE_INPUT_REQUIRED`
  (`pausar_task`), e a resposta do cliente A2A vira o retry MRTR com id novo,
  levando `inputResponses` e o `requestState` ecoado (`retomar_task`).

Sem LLM: o pedido tem formato fixo e a decisao e por regra.
Rode com `uv run python agente.py` (veja o README da raiz).
"""

from __future__ import annotations

import json
import os
import re
from contextlib import asynccontextmanager
from typing import Any

import httpx
import uvicorn
from mcp_types import CallToolResult, InputRequiredResult
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from cliente_mcp import ClienteMcp, ErroMcp, TraceContext, log
from tarefas import (
    CANCELED,
    COMPLETED,
    FAILED,
    INPUT_REQUIRED,
    WORKING,
    PausaMcp,
    RepositorioDeTasks,
    Task,
    novo_id,
)

HOST = os.environ.get("AGENTE_HOST", "127.0.0.1")
PORTA = int(os.environ.get("AGENTE_PORT", "7300"))
URL_PUBLICA = os.environ.get("AGENTE_URL_PUBLICA", f"http://127.0.0.1:{PORTA}").rstrip("/")
MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:7301/mcp")

# Mapeamento skill A2A -> capacidade MCP. O nome e conferido contra o `tools/list`
# a cada Task, e os argumentos sao montados a partir do `inputSchema` descoberto.
SKILL_RESERVAR = "reservar-sala"
TOOL_RESERVAR = "reservar_sala"
URI_POLITICA = "politica://uso"

FORMATO_PEDIDO = "reservar sala=<id> inicio=<iso8601> fim=<iso8601> responsavel=<nome>"
FORMATO_ESCOLHA = "escolha=<id da sala> ou escolha=recusar"

# Codigos de erro JSON-RPC do A2A v1.0
ERRO_PARSE = -32700
ERRO_REQUEST_INVALIDO = -32600
ERRO_METODO = -32601
ERRO_PARAMS = -32602
ERRO_TASK_NAO_ENCONTRADA = -32001
ERRO_OPERACAO_NAO_SUPORTADA = -32004

tasks = RepositorioDeTasks()
mcp: ClienteMcp | None = None


class ErroA2A(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# --------------------------------------------------------------------------- #
# Agent Card                                                                  #
# --------------------------------------------------------------------------- #


def agent_card() -> dict[str, Any]:
    return {
        "name": "Central de Salas",
        "description": "Reserva salas de reuniao da Hill Valley Tech.",
        "provider": {"organization": "Hill Valley Tech", "url": "https://hillvalley.example"},
        "version": "1.0.0",
        "supportedInterfaces": [
            {"url": f"{URL_PUBLICA}/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}
        ],
        "capabilities": {"streaming": False, "pushNotifications": False, "extendedAgentCard": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": SKILL_RESERVAR,
                "name": "Reservar sala",
                "description": "Reserva uma sala em um intervalo. Se houver conflito, pergunta qual alternativa usar.",
                "tags": ["salas", "agenda"],
                "inputModes": ["text/plain"],
                "outputModes": ["text/plain"],
                "examples": [
                    "reservar sala=sala-garagem inicio=2026-11-03T14:00:00-03:00 "
                    "fim=2026-11-03T15:00:00-03:00 responsavel=Marty"
                ],
            }
        ],
    }


# --------------------------------------------------------------------------- #
# Interpretacao do texto (formato fixo, sem LLM)                              #
# --------------------------------------------------------------------------- #

_PAR = re.compile(r"(\w+)=(.*?)(?=\s+\w+=|\s*$)", re.S)


def interpretar_pedido(texto: str) -> dict[str, str] | None:
    texto = texto.strip()
    if not texto.lower().startswith("reservar "):
        return None
    return {k: v.strip() for k, v in _PAR.findall(texto[len("reservar ") :])}


def interpretar_escolha(texto: str) -> str | None:
    m = re.fullmatch(r"\s*escolha=(\S+)\s*", texto)
    return m.group(1) if m else None


def texto_da_mensagem(mensagem: dict[str, Any]) -> str:
    return " ".join(p.get("text", "") for p in mensagem.get("parts") or [] if isinstance(p, dict)).strip()


def texto_do_resultado(resultado: CallToolResult) -> str:
    return " ".join(getattr(c, "text", "") for c in resultado.content).strip()


# --------------------------------------------------------------------------- #
# A ponte                                                                     #
# --------------------------------------------------------------------------- #


def pausar_task(task: Task, tool: str, argumentos: dict[str, Any], resultado: InputRequiredResult) -> None:
    """PONTE, ida: `resultType: input_required` do MCP vira `TASK_STATE_INPUT_REQUIRED` no A2A.

    O agente nao decide nada de dominio: repassa ao cliente A2A as opcoes que o
    servidor MCP colocou no `enum` da elicitation, na mesma ordem, e guarda o
    `requestState` (opaco) ligado a esta Task, fora de qualquer resposta A2A.
    """
    pedidos = resultado.model_dump(by_alias=True, mode="json", exclude_none=True).get("inputRequests") or {}
    if len(pedidos) != 1:
        task.transitar(FAILED, f"O servidor MCP pediu {len(pedidos)} entradas; o agente so sabe repassar uma.")
        return
    chave, pedido = next(iter(pedidos.items()))
    params = pedido.get("params") or {}
    schema = params.get("requestedSchema") or {}
    propriedades = schema.get("properties") or {}
    if pedido.get("method") != "elicitation/create" or params.get("mode", "form") != "form" or len(propriedades) != 1:
        task.transitar(FAILED, "O servidor MCP pediu uma entrada que o agente nao sabe repassar.")
        return
    campo, definicao = next(iter(propriedades.items()))
    opcoes = list(definicao.get("enum") or ([definicao["const"]] if "const" in definicao else []))
    if not opcoes or resultado.request_state is None:
        task.transitar(FAILED, "O servidor MCP pediu uma escolha sem opcoes ou sem requestState.")
        return

    task.pausa = PausaMcp(
        tool=tool,
        argumentos=argumentos,
        chave=chave,
        campo=campo,
        opcoes=opcoes,
        request_state=resultado.request_state,
    )
    task.transitar(INPUT_REQUIRED, linha_de_alternativas(opcoes))
    log(f"task {task.id} pausada: chave={chave} opcoes={opcoes} requestState guardado ({len(resultado.request_state)} chars)")


def linha_de_alternativas(opcoes: list[str]) -> str:
    return "alternativas: " + ", ".join(opcoes)


async def retomar_task(task: Task, escolha: str, trace: TraceContext) -> None:
    """PONTE, volta: a resposta do cliente A2A vira o retry do `tools/call` original.

    Mesmo nome e argumentos do request inicial, id JSON-RPC novo (o cliente MCP
    nunca repete id), `inputResponses` com a mesma chave do `inputRequests`, e o
    `requestState` ecoado sem modificacao.
    """
    pausa = task.pausa
    assert pausa is not None
    if escolha == "recusar":
        resposta: dict[str, Any] = {"action": "decline"}
    else:
        resposta = {"action": "accept", "content": {pausa.campo: escolha}}

    task.pausa = None  # o requestState e de uso unico para esta Task
    task.transitar(WORKING)
    assert mcp is not None
    resultado = await mcp.chamar_tool(
        pausa.tool,
        pausa.argumentos,
        trace,
        input_responses={pausa.chave: resposta},
        request_state=pausa.request_state,
    )
    concluir(task, pausa.tool, pausa.argumentos, resultado)


def concluir(task: Task, tool: str, argumentos: dict[str, Any], resultado: CallToolResult | InputRequiredResult) -> None:
    """Traduz o resultado MCP em estado de Task (sem regra de negocio de sala)."""
    if isinstance(resultado, InputRequiredResult):
        pausar_task(task, tool, argumentos, resultado)
        return
    if resultado.is_error:
        # Erro de execucao da tool: a mensagem exata vai para o historico da Task.
        task.transitar(FAILED, texto_do_resultado(resultado) or "A tool devolveu erro sem mensagem.")
        return
    dados = resultado.structured_content or {}
    if not dados.get("reservado", False):
        task.transitar(CANCELED, f"Reserva nao realizada: {dados.get('motivo') or 'recusado'}.")
        return
    reserva = {
        "reserva": dados.get("reserva"),
        "sala": dados.get("sala"),
        "inicio": dados.get("inicio"),
        "fim": dados.get("fim"),
        "responsavel": dados.get("responsavel"),
        "politica": task.politica,
    }
    task.artifacts.append(
        {"artifactId": novo_id("art"), "name": "reserva", "parts": [{"text": json.dumps(reserva, ensure_ascii=False)}]}
    )
    task.transitar(COMPLETED, f"Reserva {reserva['reserva']} confirmada na {reserva['sala']}.")


# --------------------------------------------------------------------------- #
# Execucao de uma Task nova                                                   #
# --------------------------------------------------------------------------- #


async def executar_pedido(task: Task, texto: str) -> None:
    assert mcp is not None and task.trace is not None
    task.transitar(WORKING)

    pedido = interpretar_pedido(texto)
    if pedido is None:
        task.transitar(FAILED, f"Pedido nao reconhecido. Use: {FORMATO_PEDIDO}")
        return

    # 1. Descoberta em runtime: nada de lista fixa de tools.
    listagem = await mcp.listar_tools(task.trace)
    tool = next((t for t in listagem.tools if t.name == TOOL_RESERVAR), None)
    if tool is None:
        task.transitar(FAILED, f"O servidor MCP nao oferece a tool {TOOL_RESERVAR}.")
        return
    propriedades = list((tool.input_schema.get("properties") or {}).keys())
    obrigatorios = tool.input_schema.get("required") or []
    faltando = [c for c in obrigatorios if c not in pedido]
    if faltando:
        task.transitar(FAILED, f"Pedido sem {', '.join(faltando)}. Use: {FORMATO_PEDIDO}")
        return
    argumentos = {c: pedido[c] for c in propriedades if c in pedido}

    # 2. Resource como escolha da aplicacao: a versao da politica vai no artifact.
    politica = await mcp.ler_resource(URI_POLITICA, task.trace)
    primeira_linha = next((getattr(c, "text", "") or "" for c in politica.contents), "").splitlines()[:1]
    if primeira_linha and primeira_linha[0].lower().startswith("versao:"):
        task.politica = primeira_linha[0].split(":", 1)[1].strip()

    # 3. A chamada. Se vier input_required, `concluir` desvia para a pausa.
    resultado = await mcp.chamar_tool(tool.name, argumentos, task.trace)
    concluir(task, tool.name, argumentos, resultado)


async def com_tratamento_de_falha(task: Task, coro: Any) -> None:
    try:
        await coro
    except ErroMcp as e:
        log(f"task {task.id}: erro de protocolo MCP {e.code}: {e.message}")
        if not task.terminal:
            task.transitar(FAILED, f"Erro do servidor MCP ({e.code}): {e.message}")
    except httpx.HTTPError as e:
        log(f"task {task.id}: servidor MCP inacessivel: {e!r}")
        if not task.terminal:
            task.transitar(FAILED, "Servidor MCP inacessivel.")


# --------------------------------------------------------------------------- #
# Metodos A2A                                                                 #
# --------------------------------------------------------------------------- #


async def send_message(params: dict[str, Any], traceparent: str | None) -> dict[str, Any]:
    mensagem = params.get("message")
    if not isinstance(mensagem, dict) or not isinstance(mensagem.get("parts"), list):
        raise ErroA2A(ERRO_PARAMS, "params.message com parts e obrigatorio")
    mensagem.setdefault("messageId", novo_id("msg"))
    texto = texto_da_mensagem(mensagem)
    trace_header = TraceContext.de_header(traceparent)

    task_id = mensagem.get("taskId")
    if not task_id:
        task = tasks.criar(mensagem.get("contextId"))
        task.trace = trace_header or TraceContext.novo()
        task.historico.append(mensagem)
        log(f"task {task.id} criada (SUBMITTED) trace-id={task.trace.trace_id}")
        async with task.trava:
            await com_tratamento_de_falha(task, executar_pedido(task, texto))
        log(f"task {task.id} -> {task.estado}")
        return {"task": task.para_wire()}

    task = tasks.obter(task_id)
    if task is None:
        raise ErroA2A(ERRO_TASK_NAO_ENCONTRADA, f"Task nao encontrada: {task_id}")
    async with task.trava:
        if task.terminal:
            raise ErroA2A(
                ERRO_OPERACAO_NAO_SUPORTADA,
                f"Task {task.id} esta em estado terminal ({task.estado}) e nao aceita novas mensagens",
            )
        if task.estado != INPUT_REQUIRED or task.pausa is None:
            raise ErroA2A(ERRO_OPERACAO_NAO_SUPORTADA, f"Task {task.id} nao esta aguardando entrada ({task.estado})")

        task.historico.append(mensagem)
        escolha = interpretar_escolha(texto)
        if escolha is None or (escolha != "recusar" and escolha not in task.pausa.opcoes):
            # Escolha fora do enum: a Task continua pausada e repete as alternativas.
            log(f"task {task.id}: escolha invalida {texto!r}, continua em INPUT_REQUIRED")
            task.transitar(INPUT_REQUIRED, linha_de_alternativas(task.pausa.opcoes))
            return {"task": task.para_wire()}

        trace = trace_header or task.trace or TraceContext.novo()
        await com_tratamento_de_falha(task, retomar_task(task, escolha, trace))
        log(f"task {task.id} -> {task.estado}")
        return {"task": task.para_wire()}


async def get_task(params: dict[str, Any]) -> dict[str, Any]:
    task_id = params.get("id")
    if not isinstance(task_id, str):
        raise ErroA2A(ERRO_PARAMS, "params.id e obrigatorio")
    task = tasks.obter(task_id)
    if task is None:
        raise ErroA2A(ERRO_TASK_NAO_ENCONTRADA, f"Task nao encontrada: {task_id}")
    history_length = params.get("historyLength")
    return {"task": task.para_wire(history_length if isinstance(history_length, int) else None)}


# --------------------------------------------------------------------------- #
# HTTP                                                                        #
# --------------------------------------------------------------------------- #


def resposta_rpc(request_id: Any, *, result: Any = None, erro: ErroA2A | None = None) -> JSONResponse:
    corpo: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if erro is not None:
        corpo["error"] = {"code": erro.code, "message": erro.message}
    else:
        corpo["result"] = result
    return JSONResponse(corpo)


async def rota_a2a(request: Request) -> JSONResponse:
    try:
        corpo = json.loads(await request.body())
    except json.JSONDecodeError:
        return resposta_rpc(None, erro=ErroA2A(ERRO_PARSE, "Parse error"))
    if not isinstance(corpo, dict) or corpo.get("jsonrpc") != "2.0" or not isinstance(corpo.get("method"), str):
        return resposta_rpc(corpo.get("id") if isinstance(corpo, dict) else None, erro=ErroA2A(ERRO_REQUEST_INVALIDO, "Invalid Request"))

    request_id = corpo.get("id")
    metodo = corpo["method"]
    params = corpo.get("params") if isinstance(corpo.get("params"), dict) else {}
    traceparent = request.headers.get("traceparent")
    log(f"<- A2A {metodo} id={json.dumps(request_id)} traceparent={traceparent or '-'}")
    try:
        if metodo == "SendMessage":
            return resposta_rpc(request_id, result=await send_message(params, traceparent))
        if metodo == "GetTask":
            return resposta_rpc(request_id, result=await get_task(params))
        raise ErroA2A(ERRO_METODO, f"Method not found: {metodo}")
    except ErroA2A as e:
        log(f"-> A2A erro {e.code}: {e.message}")
        return resposta_rpc(request_id, erro=e)


async def rota_card(request: Request) -> JSONResponse:
    return JSONResponse(agent_card())


@asynccontextmanager
async def ciclo_de_vida(app: Starlette):
    global mcp
    mcp = ClienteMcp(MCP_URL)
    log(f"agente A2A em {URL_PUBLICA}/a2a (card em {URL_PUBLICA}/.well-known/agent-card.json), MCP em {MCP_URL}")
    try:
        yield
    finally:
        await mcp.fechar()


app = Starlette(
    routes=[
        Route("/.well-known/agent-card.json", rota_card, methods=["GET"]),
        Route("/a2a", rota_a2a, methods=["POST"]),
    ],
    lifespan=ciclo_de_vida,
)


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORTA, log_level="warning")
