from __future__ import annotations

import re

from aurora.config import DADOS_DIR
from aurora.regulamento import carregar_capitulos


def trechos_de_outros_capitulos(assunto: str, tamanho: int = 60) -> list[str]:
    """Trechos (de ~60 caracteres) de cada parágrafo dos capítulos que NÃO são
    sobre ``assunto``. Se algum aparecer num evento, a Garantia 4 falhou."""
    trechos: list[str] = []
    for capitulo in carregar_capitulos(str(DADOS_DIR / "regulamento.md")):
        if capitulo.assunto == assunto:
            continue
        for paragrafo in capitulo.texto.splitlines():
            limpo = re.sub(r"\*\*[^*]+\*\*\s*", "", paragrafo).strip()
            if len(limpo) >= tamanho:
                trechos.append(limpo[:tamanho])
    return trechos
