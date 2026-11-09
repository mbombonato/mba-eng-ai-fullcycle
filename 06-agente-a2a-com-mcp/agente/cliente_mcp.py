"""Cliente MCP do agente (o lado "host" da ponte).

Fala Streamable HTTP com o servidor MCP, na revisao 2026-07-28, sem sessao:
cada request leva no `_meta` a versao do protocolo, o clientInfo e as
capabilities, e nos headers o espelho do corpo (`MCP-Protocol-Version`,
`Mcp-Method` e, quando ha alvo, `Mcp-Name`).

Por que nao o `Client` de alto nivel do SDK: ele fecha o ciclo de MRTR
sozinho, via callback de elicitation, e declara `{"form": {}, "url": {}}`.
Aqui o `input_required` precisa chegar cru ao agente, para virar pausa da
Task A2A, e a capability declarada e exatamente `{"elicitation": {"form": {}}}`.
Os resultados sao validados com os tipos do SDK oficial (`mcp_types`).
"""

from __future__ import annotations

import itertools
import json
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from mcp_types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    PROTOCOL_VERSION_META_KEY,
    CallToolResult,
    InputRequiredResult,
    ListToolsResult,
    ReadResourceResult,
)

PROTOCOLO = "2026-07-28"
CLIENT_INFO = {"name": "agente-central-de-salas", "version": "1.0.0"}
CAPABILITIES = {"elicitation": {"form": {}}}


def log(mensagem: str) -> None:
    agora = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[agente {agora}] {mensagem}", file=sys.stderr, flush=True)


class ErroMcp(Exception):
    """Erro de protocolo (JSON-RPC `error`) devolvido pelo servidor MCP."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(f"{message} (MCP {code})")
        self.code = code
        self.message = message
        self.data = data


@dataclass
class TraceContext:
    """W3C trace context de uma Task: o trace-id e fixo, o span-id e novo a cada request MCP."""

    trace_id: str
    flags: str = "01"

    @classmethod
    def de_header(cls, valor: str | None) -> TraceContext | None:
        if not valor:
            return None
        partes = valor.strip().lower().split("-")
        if len(partes) != 4 or len(partes[1]) != 32 or len(partes[2]) != 16 or len(partes[3]) != 2:
            return None
        try:
            int(partes[1], 16), int(partes[2], 16), int(partes[3], 16)
        except ValueError:
            return None
        if partes[1] == "0" * 32:
            return None
        return cls(trace_id=partes[1], flags=partes[3])

    @classmethod
    def novo(cls) -> TraceContext:
        return cls(trace_id=secrets.token_hex(16))

    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{secrets.token_hex(8)}-{self.flags}"


class ClienteMcp:
    """Um objeto cliente vivo entre chamadas (conexao HTTP reaproveitada), sem estado de protocolo."""

    def __init__(self, url: str) -> None:
        self.url = url
        self._http = httpx.AsyncClient(timeout=30.0)
        # Ids JSON-RPC monotonicamente crescentes: o retry do MRTR sempre sai com id novo.
        self._ids = itertools.count(1)

    async def fechar(self) -> None:
        await self._http.aclose()

    async def _request(self, metodo: str, params: dict[str, Any], trace: TraceContext, alvo: str | None = None) -> dict:
        request_id = next(self._ids)
        traceparent = trace.traceparent()
        corpo = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": metodo,
            "params": {
                **params,
                "_meta": {
                    PROTOCOL_VERSION_META_KEY: PROTOCOLO,
                    CLIENT_INFO_META_KEY: CLIENT_INFO,
                    CLIENT_CAPABILITIES_META_KEY: CAPABILITIES,
                    "traceparent": traceparent,
                },
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOLO,
            "Mcp-Method": metodo,
        }
        if alvo is not None:
            headers["Mcp-Name"] = alvo
        retry = " retry=sim" if "requestState" in params else ""
        log(f"-> MCP {metodo} id={request_id}{f' alvo={alvo}' if alvo else ''}{retry} traceparent={traceparent}")

        resposta = await self._http.post(self.url, json=corpo, headers=headers)
        mensagem = self._ler_resposta(resposta, request_id)
        if "error" in mensagem:
            erro = mensagem["error"]
            log(f"<- MCP id={request_id} erro {erro.get('code')} http={resposta.status_code}")
            raise ErroMcp(erro.get("code", 0), erro.get("message", ""), erro.get("data"))
        resultado = mensagem.get("result") or {}
        log(f"<- MCP id={request_id} resultType={resultado.get('resultType', 'complete')} http={resposta.status_code}")
        return resultado

    @staticmethod
    def _ler_resposta(resposta: httpx.Response, request_id: int) -> dict:
        tipo = resposta.headers.get("content-type", "")
        if tipo.startswith("text/event-stream"):
            # Streamable HTTP pode responder em SSE: procura a resposta com o nosso id.
            for linha in resposta.text.splitlines():
                if linha.startswith("data:"):
                    try:
                        msg = json.loads(linha[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    if isinstance(msg, dict) and msg.get("id") == request_id:
                        return msg
            raise ErroMcp(-32603, "resposta SSE sem a mensagem do request")
        try:
            return resposta.json()
        except json.JSONDecodeError:
            raise ErroMcp(-32603, f"resposta HTTP {resposta.status_code} sem JSON") from None

    # ----------------------------------------------------------------- metodos

    async def listar_tools(self, trace: TraceContext) -> ListToolsResult:
        return ListToolsResult.model_validate(await self._request("tools/list", {}, trace))

    async def ler_resource(self, uri: str, trace: TraceContext) -> ReadResourceResult:
        return ReadResourceResult.model_validate(await self._request("resources/read", {"uri": uri}, trace, alvo=uri))

    async def chamar_tool(
        self,
        nome: str,
        argumentos: dict[str, Any],
        trace: TraceContext,
        *,
        input_responses: dict[str, Any] | None = None,
        request_state: str | None = None,
    ) -> CallToolResult | InputRequiredResult:
        params: dict[str, Any] = {"name": nome, "arguments": argumentos}
        if input_responses is not None:
            params["inputResponses"] = input_responses
        if request_state is not None:
            params["requestState"] = request_state
        resultado = await self._request("tools/call", params, trace, alvo=nome)
        if resultado.get("resultType") == "input_required":
            return InputRequiredResult.model_validate(resultado)
        return CallToolResult.model_validate(resultado)
