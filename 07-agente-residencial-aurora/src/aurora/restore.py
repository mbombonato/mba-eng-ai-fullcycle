"""Comando de restauração: ``uv run aurora-restaurar [--sessoes]``.

Volta apartamentos, áreas, reservas e visitantes ao estado dos arquivos de
``dados/``. Por padrão as sessões são mantidas; com ``--sessoes`` o banco de
sessões do ADK também é apagado (junto do vínculo sessão→apartamento).
"""

from __future__ import annotations

import argparse

from .config import get_settings
from .db import CondominioRepository


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Restaura os dados iniciais do condomínio.")
    parser.add_argument(
        "--sessoes", action="store_true", help="também apaga todas as sessões de conversa"
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    repo = CondominioRepository(settings.db_path)
    repo.restaurar(settings.dados_dir)
    print(f"Dados do condomínio restaurados a partir de {settings.dados_dir}.")
    if args.sessoes:
        repo.apagar_sessoes()
        for sufixo in ("", "-wal", "-shm", "-journal"):
            arquivo = settings.sessions_db_path.with_name(settings.sessions_db_path.name + sufixo)
            arquivo.unlink(missing_ok=True)
        print("Sessões apagadas.")


if __name__ == "__main__":
    main()
