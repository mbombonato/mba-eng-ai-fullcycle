"""Estado das Tasks A2A, em memoria do processo do agente.

A Task publica (o que vai no wire A2A) e a pausa MCP (o que fica so aqui
dentro) sao objetos separados: o `requestState` mora em `PausaMcp`, que nunca
e serializada para o cliente A2A.
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from typing import Any

from cliente_mcp import TraceContext

SUBMITTED = "TASK_STATE_SUBMITTED"
WORKING = "TASK_STATE_WORKING"
INPUT_REQUIRED = "TASK_STATE_INPUT_REQUIRED"
COMPLETED = "TASK_STATE_COMPLETED"
CANCELED = "TASK_STATE_CANCELED"
FAILED = "TASK_STATE_FAILED"
REJECTED = "TASK_STATE_REJECTED"
TERMINAIS = {COMPLETED, CANCELED, FAILED, REJECTED}


def novo_id(prefixo: str) -> str:
    return f"{prefixo}-{secrets.token_hex(6)}"


@dataclass
class PausaMcp:
    """O que a Task precisa guardar para repetir o `tools/call` depois da resposta do cliente A2A.

    `request_state` e opaco: guardado e ecoado byte a byte, nunca aberto.
    """

    tool: str
    argumentos: dict[str, Any]
    chave: str  # a chave do inputRequests, devolvida igual no inputResponses
    campo: str  # a propriedade do requestedSchema que recebe a escolha
    opcoes: list[str]  # o enum da elicitation, na ordem recebida
    request_state: str


@dataclass
class Task:
    id: str
    context_id: str
    estado: str = SUBMITTED
    mensagem_status: dict[str, Any] | None = None
    historico: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    # ---- interno, nunca vai para o wire ----
    trace: TraceContext | None = None
    politica: str | None = None
    pausa: PausaMcp | None = None
    trava: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def terminal(self) -> bool:
        return self.estado in TERMINAIS

    def mensagem_agente(self, texto: str) -> dict[str, Any]:
        return {
            "messageId": novo_id("msg"),
            "role": "ROLE_AGENT",
            "parts": [{"text": texto}],
            "taskId": self.id,
            "contextId": self.context_id,
        }

    def transitar(self, estado: str, texto: str | None = None) -> None:
        if self.terminal:
            raise RuntimeError(f"Task {self.id} ja esta em estado terminal ({self.estado})")
        self.estado = estado
        if texto is not None:
            msg = self.mensagem_agente(texto)
            self.mensagem_status = msg
            self.historico.append(msg)
        else:
            self.mensagem_status = None

    def para_wire(self, history_length: int | None = None) -> dict[str, Any]:
        status: dict[str, Any] = {"state": self.estado}
        if self.mensagem_status is not None:
            status["message"] = self.mensagem_status
        historico = self.historico
        if history_length is not None:
            historico = historico[-history_length:] if history_length > 0 else []
        return {
            "id": self.id,
            "contextId": self.context_id,
            "status": status,
            "history": list(historico),
            "artifacts": list(self.artifacts),
        }


class RepositorioDeTasks:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def criar(self, context_id: str | None) -> Task:
        task = Task(id=novo_id("task"), context_id=context_id or novo_id("ctx"))
        self._tasks[task.id] = task
        return task

    def obter(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)
