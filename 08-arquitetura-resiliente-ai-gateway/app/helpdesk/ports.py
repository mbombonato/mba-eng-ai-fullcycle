"""Portas da aplicação: o que as features precisam do mundo externo, sem saber quem entrega."""

from collections.abc import Iterator
from datetime import date
from typing import Protocol


class TextModel(Protocol):
    """Gera texto para uma capacidade lógica (ex.: "ticket-classification").

    Quem implementa decide o provider, o modelo físico, o retry e o fallback; a feature
    só conhece a capacidade. Falhas chegam como exceções de `errors`.
    """

    def complete(self, capability: str, task: str, content: str) -> str: ...

    def stream(self, capability: str, task: str, content: str) -> Iterator[str]: ...


class TicketSource(Protocol):
    """Fonte dos tickets abertos num período (datas inclusivas)."""

    def in_period(self, start: date, end: date) -> list[dict]: ...
