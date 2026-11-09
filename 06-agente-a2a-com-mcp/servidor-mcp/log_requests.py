"""Registro de cada request JSON-RPC no stderr (metodo, id, traceparent, HTTP status).

Fica na borda ASGI, antes do SDK, para registrar tambem os requests que o SDK
recusa (sem `_meta`, header divergente, capability faltando).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any


def log(mensagem: str) -> None:
    agora = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[mcp {agora}] {mensagem}", file=sys.stderr, flush=True)


def _resumo(corpo: bytes) -> list[str]:
    try:
        dados = json.loads(corpo or b"null")
    except json.JSONDecodeError:
        return ["metodo=? id=? (corpo nao e JSON)"]
    mensagens = dados if isinstance(dados, list) else [dados]
    linhas = []
    for m in mensagens:
        if not isinstance(m, dict):
            continue
        params = m.get("params") if isinstance(m.get("params"), dict) else {}
        meta = params.get("_meta") if isinstance(params.get("_meta"), dict) else {}
        alvo = params.get("name") or params.get("uri")
        extra = f" alvo={alvo}" if alvo else ""
        if "requestState" in params:
            extra += " retry=sim"
        linhas.append(
            f"metodo={m.get('method')} id={json.dumps(m.get('id'))}{extra} traceparent={meta.get('traceparent', '-')}"
        )
    return linhas


class RequestLogMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        partes: list[bytes] = []
        mais = True
        while mais:
            msg = await receive()
            partes.append(msg.get("body", b""))
            mais = msg.get("more_body", False)
        corpo = b"".join(partes)
        for linha in _resumo(corpo):
            log(f"recebido {linha}")
        if os.environ.get("MCP_LOG_BODY") == "1":
            cabecalhos = {k.decode(): v.decode() for k, v in scope.get("headers", []) if k.lower().startswith(b"mcp")}
            log(f"  headers={json.dumps(cabecalhos)} corpo={corpo.decode(errors='replace')}")
        entregue = False

        async def receive_replay() -> dict:
            nonlocal entregue
            if not entregue:
                entregue = True
                return {"type": "http.request", "body": corpo, "more_body": False}
            return await receive()

        async def send_com_log(msg: dict) -> None:
            if msg["type"] == "http.response.start":
                log(f"respondido http={msg['status']}")
            await send(msg)

        await self.app(scope, receive_replay, send_com_log)
