"""LLM falso e determinístico para testar o ADK de ponta a ponta sem chave.

Ele imita um modelo "obediente" com regras simples por palavra-chave e também
pode ser configurado para agir de forma maliciosa (``malicioso=True``), por
exemplo tentando cancelar a reserva de outro apartamento pelo código. Os testes
mostram que as garantias valem mesmo assim, porque estão no código.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

DATA_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
NOME_RE = re.compile(
    r"\b(?:d[aoe]|para|visitante)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ú]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ú]+)+)"
)


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def _area(texto: str) -> str | None:
    t = _norm(texto)
    if "salao" in t:
        return "salao-de-festas"
    if "churrasq" in t:
        return "churrasqueira"
    if "quadra" in t:
        return "quadra"
    return None


def _call(name: str, **args: Any) -> LlmResponse:
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))],
        )
    )


def _text(texto: str) -> LlmResponse:
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text=texto)])
    )


class FakeLlm(BaseLlm):
    model: str = "fake-aurora"
    malicioso: bool = False
    chamadas: int = 0

    @classmethod
    def supported_models(cls) -> list[str]:
        return ["fake-aurora"]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        self.chamadas += 1
        yield self._decidir(llm_request)

    # ------------------------------------------------------------------
    def _decidir(self, req: LlmRequest) -> LlmResponse:
        tools = set(req.tools_dict)
        texto, respostas = self._ultimo_pedido(req.contents)

        if "consultar_regulamento" in tools:
            return self._regulamento(texto, respostas)
        if "reservar_area" in tools:
            return self._reservas(texto, respostas)
        if "autorizar_visitante" in tools:
            return self._visitantes(texto, respostas)
        return self._principal(texto, respostas)

    @staticmethod
    def _ultimo_pedido(contents: list[types.Content]) -> tuple[str, list[types.FunctionResponse]]:
        """Último texto do morador e as respostas de tool que vieram depois dele."""
        respostas: list[types.FunctionResponse] = []
        for content in reversed(contents):
            partes = content.parts or []
            if partes and (partes[0].text or "").startswith("For context"):
                continue
            for part in reversed(partes):
                if part.function_response:
                    respostas.insert(0, part.function_response)
                if content.role == "user" and part.text:
                    return part.text, respostas
        return "", respostas

    # ------------------------------------------------------------ agentes
    def _principal(self, texto: str, respostas) -> LlmResponse:
        for r in respostas:
            if r.name == "especialista_regulamento":
                return _text(str((r.response or {}).get("result", "")))
        t = _norm(texto)
        if "visitante" in t or "libera" in t or "entrada" in t:
            if "reserva" in t and ("quais" in t or "tem" in t):
                return _call("transfer_to_agent", agent_name="especialista_reservas")
            return _call("transfer_to_agent", agent_name="especialista_visitantes")
        if "reserv" in t or "cancel" in t:
            return _call("transfer_to_agent", agent_name="especialista_reservas")
        if respostas:
            return _text("Posso ajudar em algo mais?")
        return _call("especialista_regulamento", request=texto)

    def _reservas(self, texto: str, respostas) -> LlmResponse:
        proprias = [r for r in respostas if r.name != "transfer_to_agent"]
        if proprias:
            r = proprias[-1]
            return _text(f"Resultado de {r.name}: {json.dumps(r.response, ensure_ascii=False)}")
        t = _norm(texto)
        datas = DATA_RE.findall(texto)
        area = _area(texto)
        if "reserv" not in t and "cancel" not in t:
            return _call("transfer_to_agent", agent_name="assistente_aurora")
        if "cancel" in t:
            if self.malicioso:
                return _call("cancelar_minha_reserva", codigo="RSV-4821")
            if area and datas:
                return _call("cancelar_minha_reserva", area=area, data=datas[0])
            m = re.search(r"RSV-[\w]+", texto)
            return _call("cancelar_minha_reserva", codigo=m.group(0) if m else "")
        if "reserve" in t or "reservar" in t:
            if area and datas:
                return _call("reservar_area", area=area, data=datas[0])
        if "reserva" in t:
            return _call("listar_minhas_reservas")
        return _text("Não entendi o pedido de reserva.")

    def _visitantes(self, texto: str, respostas) -> LlmResponse:
        proprias = [r for r in respostas if r.name != "transfer_to_agent"]
        if proprias:
            r = proprias[-1]
            return _text(f"Resultado de {r.name}: {json.dumps(r.response, ensure_ascii=False)}")
        t = _norm(texto)
        datas = DATA_RE.findall(texto)
        m = NOME_RE.search(texto)
        if ("libera" in t or "autoriz" in t or "entrada" in t) and m and datas:
            return _call("autorizar_visitante", nome=m.group(1), data=datas[0])
        if "visitante" in t:
            return _call("listar_meus_visitantes")
        return _call("transfer_to_agent", agent_name="assistente_aurora")

    def _regulamento(self, texto: str, respostas) -> LlmResponse:
        if not respostas:
            return _call("consultar_regulamento", assunto=texto)
        resposta = respostas[-1].response or {}
        corpo = str(resposta.get("texto", ""))
        termos = {w for w in re.findall(r"[a-z]{4,}", _norm(texto))}
        melhor = max(
            corpo.splitlines() or [""],
            key=lambda linha: sum(1 for w in termos if w[:5] in _norm(linha)),
        )
        return _text(melhor.strip() or "O regulamento não trata desse assunto.")
