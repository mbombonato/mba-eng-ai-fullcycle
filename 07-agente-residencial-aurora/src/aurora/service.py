"""Camada de aplicação: sessões, execução do Runner e confirmações.

Garantia 1 (confirmação vem do sistema): a lista de confirmações pendentes é
calculada a partir dos eventos persistidos da sessão (chamadas
``adk_request_confirmation`` sem ``FunctionResponse`` correspondente). A rota de
confirmações só aceita um ``id`` dessa lista; qualquer outro recebe 409 antes
de chegar ao Runner. A resposta aprovada/negada é entregue ao ADK como uma
``FunctionResponse`` de ``adk_request_confirmation``, o que faz o Runner
retomar a execução no agente que pediu a confirmação (o autor da chamada
original) e reexecutar a tool com ``tool_context.tool_confirmation``.

Garantia 3 (nada se perde no reinício): sessões e eventos ficam no SQLite via
``DatabaseSessionService``; reservas/visitantes ficam em ``condominio.db``.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from google.adk.events.event import Event
from google.adk.flows.llm_flows.functions import REQUEST_CONFIRMATION_FUNCTION_CALL_NAME
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions.session import Session
from google.genai import types

from .agents import APP_NAME, Modelo, build_app, build_root_agent
from .config import Settings
from .db import CondominioRepository
from .tools import STATE_APARTAMENTO

logger = logging.getLogger(__name__)


def resolver_modelo(nome: str, provedor: str) -> Modelo:
    """Gemini: o ADK resolve pelo nome. OpenAI (opcional): LiteLlm."""
    if provedor == "openai" or nome.startswith("openai/"):
        from google.adk.models.lite_llm import LiteLlm  # requer o extra "openai"

        return LiteLlm(model=nome if "/" in nome else f"openai/{nome}")
    return nome


class SessaoNaoEncontrada(LookupError):
    pass


class ConfirmacaoInexistente(LookupError):
    pass


@dataclass
class RespostaConversa:
    resposta: str
    confirmacoes_pendentes: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resposta": self.resposta,
            "confirmacoes_pendentes": self.confirmacoes_pendentes,
        }


def _user_id(apartamento: str) -> str:
    return f"apartamento-{apartamento}"


def confirmacoes_pendentes(session: Session) -> list[dict[str, Any]]:
    """Confirmações pedidas por tools e ainda sem resposta, na ordem dos eventos."""
    pedidas: dict[str, dict[str, Any]] = {}
    respondidas: set[str] = set()
    for event in session.events:
        for call in event.get_function_calls():
            if call.name == REQUEST_CONFIRMATION_FUNCTION_CALL_NAME and call.id:
                args = call.args or {}
                original = args.get("originalFunctionCall") or {}
                confirmacao = args.get("toolConfirmation") or {}
                pedidas[call.id] = {
                    "id": call.id,
                    "acao": original.get("name", ""),
                    "detalhes": confirmacao.get("payload") or original.get("args") or {},
                    "descricao": confirmacao.get("hint", ""),
                }
        for resp in event.get_function_responses():
            if resp.name == REQUEST_CONFIRMATION_FUNCTION_CALL_NAME and resp.id:
                respondidas.add(resp.id)
    return [p for i, p in pedidas.items() if i not in respondidas]


def _texto_do_evento(event: Event) -> str:
    if event.author == "user" or not event.content or not event.content.parts:
        return ""
    if event.partial:
        return ""
    partes = [
        p.text
        for p in event.content.parts
        if p.text and not getattr(p, "thought", False)
    ]
    return "".join(partes).strip()


class AuroraService:
    def __init__(
        self,
        settings: Settings,
        *,
        modelo_principal: Modelo | None = None,
        modelo_especialistas: Modelo | None = None,
        session_service: BaseSessionService | None = None,
    ):
        self.settings = settings
        self.repo = CondominioRepository(settings.db_path)
        if self.repo.esta_vazio():
            self.repo.restaurar(settings.dados_dir)
        settings.sessions_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_service = session_service or DatabaseSessionService(
            db_url=f"sqlite+aiosqlite:///{settings.sessions_db_path}"
        )
        self.root_agent = build_root_agent(
            self.repo,
            str(settings.dados_dir / "regulamento.md"),
            modelo_principal
            or resolver_modelo(settings.modelo_principal, settings.provedor),
            modelo_especialistas
            or resolver_modelo(settings.modelo_especialistas, settings.provedor),
        )
        self.app = build_app(self.root_agent)
        self.runner = Runner(app=self.app, session_service=self.session_service)
        self._locks: dict[str, asyncio.Lock] = {}

    async def close(self) -> None:
        await self.runner.close()
        close = getattr(self.session_service, "close", None)
        if close:
            await close()

    # ---------------------------------------------------------------- sessões
    async def criar_sessao(self, apartamento: str) -> str:
        apartamento = str(apartamento).strip()
        session = await self.session_service.create_session(
            app_name=APP_NAME,
            user_id=_user_id(apartamento),
            # Garantia 2: o apartamento é definido aqui, uma única vez.
            state={STATE_APARTAMENTO: apartamento},
        )
        self.repo.registrar_sessao(session.id, apartamento)
        return session.id

    async def _carregar(self, session_id: str) -> Session:
        apartamento = self.repo.apartamento_registrado(session_id)
        if apartamento is None:
            raise SessaoNaoEncontrada(session_id)
        session = await self.session_service.get_session(
            app_name=APP_NAME, user_id=_user_id(apartamento), session_id=session_id
        )
        if session is None:
            raise SessaoNaoEncontrada(session_id)
        return session

    async def eventos(self, session_id: str) -> list[dict[str, Any]]:
        session = await self._carregar(session_id)
        return [
            e.model_dump(mode="json", exclude_none=True, by_alias=True)
            for e in session.events
        ]

    async def pendentes(self, session_id: str) -> list[dict[str, Any]]:
        return confirmacoes_pendentes(await self._carregar(session_id))

    # --------------------------------------------------------------- execução
    def _lock(self, session_id: str) -> asyncio.Lock:
        return self._locks.setdefault(session_id, asyncio.Lock())

    async def _executar(self, session: Session, mensagem: types.Content) -> RespostaConversa:
        textos: list[str] = []
        async for event in self.runner.run_async(
            user_id=session.user_id, session_id=session.id, new_message=mensagem
        ):
            texto = _texto_do_evento(event)
            if texto:
                textos.append(texto)
        atualizada = await self._carregar(session.id)
        return RespostaConversa(
            resposta="\n\n".join(textos),
            confirmacoes_pendentes=confirmacoes_pendentes(atualizada),
        )

    async def enviar_mensagem(self, session_id: str, texto: str) -> RespostaConversa:
        async with self._lock(session_id):
            session = await self._carregar(session_id)
            mensagem = types.Content(role="user", parts=[types.Part(text=texto)])
            return await self._executar(session, mensagem)

    async def responder_confirmacao(
        self, session_id: str, confirmacao_id: str, confirmado: bool
    ) -> RespostaConversa:
        async with self._lock(session_id):
            session = await self._carregar(session_id)
            pendentes = {p["id"] for p in confirmacoes_pendentes(session)}
            if confirmacao_id not in pendentes:
                # Id inexistente, de outra sessão ou já respondido: nada executa.
                raise ConfirmacaoInexistente(confirmacao_id)
            mensagem = types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=confirmacao_id,
                            name=REQUEST_CONFIRMATION_FUNCTION_CALL_NAME,
                            response={"confirmed": bool(confirmado)},
                        )
                    )
                ],
            )
            return await self._executar(session, mensagem)
