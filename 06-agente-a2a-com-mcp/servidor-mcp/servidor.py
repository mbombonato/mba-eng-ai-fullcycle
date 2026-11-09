"""Servidor MCP da Central de Salas (Hill Valley Tech).

Streamable HTTP stateless em http://127.0.0.1:7301/mcp, revisao 2026-07-28 da spec.

- tools: listar_salas, consultar_disponibilidade, reservar_sala
- resource: politica://uso
- MRTR na reserva: em conflito, `reservar_sala` devolve um `InputRequiredResult`
  (elicitation em form mode + `requestState`), que o SDK sela com AES-256-GCM
  via `RequestStateSecurity`; no retry, o pedido e reconstruido do estado selado.

Rode com `uv run python servidor.py` (veja o README da raiz).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, create_model

from mcp.server import MCPServer
from mcp.server.elicitation import render_elicitation_schema
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.request_state import RequestStateSecurity
from mcp.shared.exceptions import MCPError
from mcp_types import (
    MISSING_REQUIRED_CLIENT_CAPABILITY,
    ElicitRequest,
    ElicitRequestFormParams,
    ElicitResult,
    InputRequiredResult,
)

from log_requests import RequestLogMiddleware, log

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"

NOME_SERVIDOR = "central-de-salas"
FUSO_SP = timezone(timedelta(hours=-3))
JANELA_INICIO = (8, 0)
JANELA_FIM = (20, 0)
DURACAO_MAXIMA = timedelta(hours=2)
MAX_ALTERNATIVAS = 3
REQUEST_STATE_TTL_SEGUNDOS = 600  # 10 minutos (o enunciado pede entre 5 e 30)

MSG_SALA_INEXISTENTE = "Sala inexistente: {sala}"
MSG_JANELA = "Fora da janela de uso: a politica permite reservas entre 08:00 e 20:00"
MSG_DURACAO = "Duracao acima do limite: a politica permite no maximo 2 horas"
MSG_INTERVALO = "Intervalo invalido: fim deve ser posterior a inicio"
MSG_SEM_ALTERNATIVAS = "Sem alternativas disponiveis no intervalo"
MSG_ELICITATION = "A sala pedida esta ocupada nesse intervalo. Escolha uma alternativa."
CHAVE_ESCOLHA = "escolha_de_sala"  # chave do inputRequests, atribuida por este servidor


# --------------------------------------------------------------------------- #
# Configuracao                                                                #
# --------------------------------------------------------------------------- #


def carregar_dotenv() -> None:
    """Le `.env` da raiz do repositorio, sem sobrescrever o ambiente."""
    caminho = RAIZ / ".env"
    if not caminho.is_file():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.removeprefix("export ").strip()
        valor = valor.strip().strip('"').strip("'")
        if valor:
            os.environ.setdefault(chave, valor)


def chave_de_integridade() -> bytes:
    """A chave do `requestState` vem de REQUEST_STATE_SECRET, nunca do codigo."""
    bruto = os.environ.get("REQUEST_STATE_SECRET", "").strip()
    if not bruto:
        sys.exit(
            "REQUEST_STATE_SECRET nao definida. Gere com:\n"
            '  python3 -c "import secrets; print(secrets.token_hex(32))"\n'
            "e exporte antes de subir o servidor (veja o README)."
        )
    try:
        chave = bytes.fromhex(bruto)
    except ValueError:
        chave = bruto.encode()
    if len(chave) < 32:
        sys.exit(f"REQUEST_STATE_SECRET precisa ter no minimo 32 bytes (tem {len(chave)}).")
    return chave


carregar_dotenv()


# --------------------------------------------------------------------------- #
# Dominio: dados em memoria                                                    #
# --------------------------------------------------------------------------- #

SALAS: list[dict[str, Any]] = json.loads((DADOS / "salas.json").read_text(encoding="utf-8"))
SALAS_POR_ID = {s["id"]: s for s in SALAS}
RESERVAS: list[dict[str, Any]] = json.loads((DADOS / "reservas.json").read_text(encoding="utf-8"))
POLITICA_TEXTO = (DADOS / "politica-de-uso.md").read_text(encoding="utf-8")
POLITICA_VERSAO = POLITICA_TEXTO.splitlines()[0].split(":", 1)[1].strip()


def proximo_id_reserva() -> str:
    maior = max((int(r["id"].split("-")[1]) for r in RESERVAS), default=0)
    return f"res-{maior + 1:04d}"


def parse_instante(valor: str) -> datetime:
    try:
        instante = datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ToolError(f"Instante invalido: {valor!r} nao e ISO 8601") from None
    if instante.tzinfo is None:
        # Sem offset, assume o horario de Sao Paulo declarado na politica.
        instante = instante.replace(tzinfo=FUSO_SP)
    return instante


def validar(sala: str, inicio: str, fim: str) -> tuple[datetime, datetime]:
    """Regras de sala e de politica, na ordem: sala, intervalo, janela, duracao."""
    if sala not in SALAS_POR_ID:
        raise ToolError(MSG_SALA_INEXISTENTE.format(sala=sala))
    ini, fi = parse_instante(inicio), parse_instante(fim)
    if fi <= ini:
        raise ToolError(MSG_INTERVALO)
    ini_sp, fim_sp = ini.astimezone(FUSO_SP), fi.astimezone(FUSO_SP)
    abre = ini_sp.replace(hour=JANELA_INICIO[0], minute=JANELA_INICIO[1], second=0, microsecond=0)
    fecha = ini_sp.replace(hour=JANELA_FIM[0], minute=JANELA_FIM[1], second=0, microsecond=0)
    if not (abre <= ini_sp <= fecha and abre <= fim_sp <= fecha):
        raise ToolError(MSG_JANELA)
    if fi - ini > DURACAO_MAXIMA:
        raise ToolError(MSG_DURACAO)
    return ini, fi


def conflitos(sala: str, ini: datetime, fi: datetime) -> list[dict[str, Any]]:
    return [
        r
        for r in RESERVAS
        if r["sala"] == sala and parse_instante(r["inicio"]) < fi and ini < parse_instante(r["fim"])
    ]


def alternativas(sala: str, ini: datetime, fi: datetime) -> list[str]:
    """Salas livres no intervalo com capacidade >= a pedida; ate 3, por (capacidade, id)."""
    capacidade = SALAS_POR_ID[sala]["capacidade"]
    candidatas = [
        s
        for s in SALAS
        if s["id"] != sala and s["capacidade"] >= capacidade and not conflitos(s["id"], ini, fi)
    ]
    candidatas.sort(key=lambda s: (s["capacidade"], s["id"]))
    return [s["id"] for s in candidatas[:MAX_ALTERNATIVAS]]


# --------------------------------------------------------------------------- #
# Schemas de saida                                                            #
# --------------------------------------------------------------------------- #


class SalaOut(BaseModel):
    id: str
    nome: str
    capacidade: int
    recursos: list[str]


class ListaDeSalas(BaseModel):
    salas: list[SalaOut]


class ConflitoOut(BaseModel):
    id: str
    inicio: str
    fim: str
    responsavel: str


class Disponibilidade(BaseModel):
    sala: str
    livre: bool
    conflitos: list[ConflitoOut]


class ReservaOut(BaseModel):
    reserva: Optional[str] = None
    reservado: bool = True
    sala: Optional[str] = None
    inicio: Optional[str] = None
    fim: Optional[str] = None
    responsavel: Optional[str] = None
    politica: Optional[str] = None
    motivo: Optional[str] = None


def schema_de_escolha(opcoes: list[str]) -> type[BaseModel]:
    """Schema plano da elicitation: uma propriedade `sala` restrita as alternativas."""
    return create_model(
        "EscolhaDeSala",
        sala=(
            Literal[tuple(opcoes)],  # type: ignore[valid-type]
            Field(title="Sala", description="Sala alternativa escolhida"),
        ),
    )


# --------------------------------------------------------------------------- #
# Servidor MCP                                                                 #
# --------------------------------------------------------------------------- #

mcp = MCPServer(
    NOME_SERVIDOR,
    version="1.0.0",
    request_state_security=RequestStateSecurity(
        keys=[chave_de_integridade()],
        ttl=REQUEST_STATE_TTL_SEGUNDOS,
        audience=NOME_SERVIDOR,
    ),
)


@mcp.tool()
def listar_salas() -> ListaDeSalas:
    """Lista todas as salas com capacidade e recursos."""
    return ListaDeSalas(salas=[SalaOut(**s) for s in SALAS])


@mcp.tool()
def consultar_disponibilidade(sala: str, inicio: str, fim: str) -> Disponibilidade:
    """Diz se uma sala esta livre no intervalo, e quais reservas conflitam."""
    ini, fi = validar(sala, inicio, fim)
    achados = conflitos(sala, ini, fi)
    return Disponibilidade(
        sala=sala,
        livre=not achados,
        conflitos=[ConflitoOut(**{k: r[k] for k in ("id", "inicio", "fim", "responsavel")}) for r in achados],
    )


def exigir_elicitation_form(ctx: Context) -> None:
    """Sem a capability de elicitation em form mode, nao ha pergunta: -32021 (HTTP 400).

    A capability e lida do `_meta` deste request (o SDK nao guarda sessao);
    `{"elicitation": {}}` sem modos conta como form, como manda a spec.
    """
    caps = ctx.client_capabilities
    elicitation = caps.elicitation if caps is not None else None
    if elicitation is not None and (elicitation.form is not None or elicitation.url is None):
        return
    raise MCPError(
        code=MISSING_REQUIRED_CLIENT_CAPABILITY,
        message="Client did not declare the form elicitation capability required by reservar_sala",
        data={"requiredCapabilities": {"elicitation": {"form": {}}}},
    )


def pedir_escolha(ctx: Context, pedido: dict[str, str], opcoes: list[str]) -> InputRequiredResult:
    """Termina a resposta pedindo informacao (MRTR): nao existe canal de volta.

    O `requestState` leva o pedido original e as alternativas oferecidas. Aqui
    ele sai em texto puro: a `RequestStateBoundary` do SDK o envelopa com
    expiracao, digest dos argumentos e audiencia, e sela com AES-256-GCM sob a
    chave de REQUEST_STATE_SECRET antes de ir para o wire.
    """
    exigir_elicitation_form(ctx)
    estado = {"v": 1, "pedido": pedido, "opcoes": opcoes}
    return InputRequiredResult(
        input_requests={
            CHAVE_ESCOLHA: ElicitRequest(
                params=ElicitRequestFormParams(
                    mode="form",
                    message=MSG_ELICITATION,
                    requested_schema=render_elicitation_schema(schema_de_escolha(opcoes)),
                )
            )
        },
        request_state=json.dumps(estado, separators=(",", ":")),
    )


def criar_reserva(sala: str, inicio: str, fim: str, responsavel: str) -> ReservaOut:
    reserva = {"id": proximo_id_reserva(), "sala": sala, "inicio": inicio, "fim": fim, "responsavel": responsavel}
    RESERVAS.append(reserva)
    log(f"reserva criada id={reserva['id']} sala={sala} inicio={inicio} fim={fim} responsavel={responsavel}")
    return ReservaOut(
        reserva=reserva["id"],
        reservado=True,
        sala=sala,
        inicio=inicio,
        fim=fim,
        responsavel=responsavel,
        politica=POLITICA_VERSAO,
    )


def tentar_reservar(ctx: Context, pedido: dict[str, str], sala: str) -> ReservaOut | InputRequiredResult:
    """Reserva `sala` no intervalo do pedido; em conflito, pergunta (ou falha sem alternativas)."""
    ini, fi = validar(sala, pedido["inicio"], pedido["fim"])
    if not conflitos(sala, ini, fi):
        return criar_reserva(sala, pedido["inicio"], pedido["fim"], pedido["responsavel"])
    opcoes = alternativas(pedido["sala"], ini, fi)
    if not opcoes:
        raise ToolError(MSG_SEM_ALTERNATIVAS)
    return pedir_escolha(ctx, pedido, opcoes)


@mcp.tool()
def reservar_sala(sala: str, inicio: str, fim: str, responsavel: str, ctx: Context) -> ReservaOut | InputRequiredResult:
    """Reserva uma sala. Se o intervalo estiver ocupado, pergunta qual alternativa usar."""
    if ctx.request_state is None:
        # Rodada inicial.
        pedido = {"sala": sala, "inicio": inicio, "fim": fim, "responsavel": responsavel}
        return tentar_reservar(ctx, pedido, sala)

    # Retry. Quando chegamos aqui, o SDK ja verificou a integridade, a expiracao e o
    # vinculo do `requestState` com os argumentos deste request; o texto abaixo e o que
    # este servidor selou. O pedido e reconstruido dele, nunca dos argumentos reenviados,
    # e nada foi guardado em memoria entre as rodadas (sobrevive a restart).
    estado = json.loads(ctx.request_state)
    pedido: dict[str, str] = estado["pedido"]
    opcoes: list[str] = estado["opcoes"]
    resposta = (ctx.input_responses or {}).get(CHAVE_ESCOLHA)
    if not isinstance(resposta, ElicitResult):
        # Retry sem a resposta da elicitation: repete a mesma pergunta.
        return pedir_escolha(ctx, pedido, opcoes)
    if resposta.action != "accept":
        # decline/cancel nao e erro: conclui sem reservar.
        return ReservaOut(reservado=False, motivo="recusado" if resposta.action == "decline" else "cancelado")
    escolha = (resposta.content or {}).get("sala")
    if escolha not in opcoes:
        raise ToolError(f"Escolha invalida: {escolha} nao esta entre as alternativas oferecidas ({', '.join(opcoes)})")
    return tentar_reservar(ctx, pedido, escolha)


@mcp.resource("politica://uso", name="politica-de-uso", mime_type="text/markdown")
def politica_de_uso() -> str:
    """Politica de uso das salas. A primeira linha declara a versao."""
    return POLITICA_TEXTO


def main() -> None:
    import uvicorn

    host = os.environ.get("MCP_HOST", "127.0.0.1")
    porta = int(os.environ.get("MCP_PORT", "7301"))
    app = mcp.streamable_http_app(streamable_http_path="/mcp", stateless_http=True, json_response=True, host=host)
    log(f"servidor MCP {NOME_SERVIDOR} em http://{host}:{porta}/mcp (politica {POLITICA_VERSAO})")
    uvicorn.run(RequestLogMiddleware(app), host=host, port=porta, log_level="warning")


if __name__ == "__main__":
    main()
