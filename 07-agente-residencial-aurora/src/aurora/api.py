"""API HTTP (FastAPI) do assistente do Residencial Aurora."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import get_settings
from .service import AuroraService, ConfirmacaoInexistente, SessaoNaoEncontrada

logger = logging.getLogger(__name__)


class CriarSessao(BaseModel):
    apartamento: str


class Mensagem(BaseModel):
    texto: str


class Confirmacao(BaseModel):
    id: str
    confirmado: bool


def create_app(service_factory: Callable[[], AuroraService] | None = None) -> FastAPI:
    factory = service_factory or (lambda: AuroraService(get_settings()))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.service = factory()
        try:
            yield
        finally:
            await app.state.service.close()

    app = FastAPI(title="Assistente do Residencial Aurora", lifespan=lifespan)

    def svc() -> AuroraService:
        return app.state.service

    @app.exception_handler(SessaoNaoEncontrada)
    async def _sessao_nao_encontrada(_, exc: SessaoNaoEncontrada):
        return JSONResponse(status_code=404, content={"detail": "Sessão não encontrada."})

    @app.exception_handler(ConfirmacaoInexistente)
    async def _confirmacao_inexistente(_, exc: ConfirmacaoInexistente):
        return JSONResponse(
            status_code=409,
            content={"detail": "Não existe confirmação pendente com esse id nesta sessão."},
        )

    @app.post("/sessoes", status_code=201)
    async def criar_sessao(body: CriarSessao) -> dict[str, str]:
        apartamento = body.apartamento.strip()
        if not apartamento:
            raise HTTPException(status_code=422, detail="Informe o apartamento.")
        return {"session_id": await svc().criar_sessao(apartamento)}

    async def _conversar(coro) -> dict[str, Any]:
        try:
            return (await coro).to_dict()
        except (SessaoNaoEncontrada, ConfirmacaoInexistente):
            raise
        except Exception as exc:  # falha do modelo/provedor (chave, cota, rede)
            logger.exception("Falha ao executar o agente")
            raise HTTPException(
                status_code=502, detail=f"Falha ao executar o agente: {exc}"
            ) from exc

    @app.post("/sessoes/{session_id}/mensagens")
    async def enviar_mensagem(session_id: str, body: Mensagem) -> dict[str, Any]:
        return await _conversar(svc().enviar_mensagem(session_id, body.texto))

    @app.post("/sessoes/{session_id}/confirmacoes")
    async def responder_confirmacao(session_id: str, body: Confirmacao) -> dict[str, Any]:
        return await _conversar(
            svc().responder_confirmacao(session_id, body.id, body.confirmado)
        )

    @app.get("/sessoes/{session_id}/eventos")
    async def eventos(session_id: str) -> list[dict[str, Any]]:
        return await svc().eventos(session_id)

    # ---------------------------------------------- rotas de verificação
    @app.get("/apartamentos/{numero}/reservas")
    async def reservas(numero: str) -> list[dict[str, str]]:
        return [
            {"codigo": r.codigo, "area": r.area, "data": r.data}
            for r in svc().repo.reservas_do_apartamento(numero)
        ]

    @app.get("/apartamentos/{numero}/visitantes")
    async def visitantes(numero: str) -> list[dict[str, str]]:
        return svc().repo.visitantes_do_apartamento(numero)

    return app


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    uvicorn.run(create_app(), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
