"""Consulta ao regulamento interno (Garantia 4).

O regulamento é dividido em capítulos (cabeçalhos ``## ``). A consulta escolhe,
em código, UM único capítulo relevante para o assunto pedido e devolve só ele.
Assim o texto completo nunca vai para nenhum prompt nem para nenhum evento, e
mesmo o especialista de regulamento só enxerga o capítulo do assunto.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .db import normalizar

_STOPWORDS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na",
    "nos", "nas", "um", "uma", "para", "por", "com", "que", "qual", "quais",
    "como", "ate", "se", "ao", "aos", "pode", "posso", "sobre", "regra",
    "regras", "regulamento", "horas", "hora", "e", "ou", "meu", "minha", "eu",
    "funciona", "quando", "onde", "tem", "ha", "sao", "esta", "ser",
}


@dataclass(frozen=True)
class Capitulo:
    titulo: str
    texto: str  # inclui o próprio título

    @property
    def assunto(self) -> str:
        return self.titulo.split(":", 1)[-1].strip()


def _radicais(texto: str) -> list[str]:
    palavras = re.findall(r"[a-z0-9]+", normalizar(texto))
    return [p[:6] for p in palavras if len(p) > 2 and p not in _STOPWORDS]


def dividir_capitulos(markdown: str) -> list[Capitulo]:
    capitulos: list[Capitulo] = []
    partes = re.split(r"(?m)^## ", markdown)
    for parte in partes[1:]:
        titulo = parte.splitlines()[0].strip()
        capitulos.append(Capitulo(titulo=titulo, texto="## " + parte.strip()))
    return capitulos


@lru_cache(maxsize=4)
def carregar_capitulos(caminho: str) -> tuple[Capitulo, ...]:
    return tuple(dividir_capitulos(Path(caminho).read_text("utf-8")))


def _pontuar(capitulo: Capitulo, termos: list[str]) -> float:
    titulo = set(_radicais(capitulo.titulo))
    corpo = _radicais(capitulo.texto)
    total = len(corpo) or 1
    pontos = 0.0
    for termo in set(termos):
        if termo in titulo:
            pontos += 10
        ocorrencias = corpo.count(termo)
        if ocorrencias:
            pontos += 1 + 100 * ocorrencias / total
    return pontos


def escolher_capitulo(capitulos: tuple[Capitulo, ...], assunto: str) -> Capitulo | None:
    termos = _radicais(assunto)
    if not termos:
        return None
    melhor = max(capitulos, key=lambda c: _pontuar(c, termos))
    return melhor if _pontuar(melhor, termos) > 0 else None


def listar_assuntos(capitulos: tuple[Capitulo, ...]) -> list[str]:
    return [c.assunto for c in capitulos]


def buscar_capitulo(capitulos: tuple[Capitulo, ...], assunto: str) -> Capitulo | None:
    """Primeiro tenta casar com o título de um capítulo; depois, por relevância."""
    alvo = normalizar(assunto)
    for capitulo in capitulos:
        if alvo and alvo in (normalizar(capitulo.titulo), normalizar(capitulo.assunto)):
            return capitulo
    return escolher_capitulo(capitulos, assunto)
