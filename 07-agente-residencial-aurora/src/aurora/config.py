"""Configuração central: caminhos, modelos e variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DADOS_DIR = PROJECT_ROOT / "dados"

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    dados_dir: Path
    db_path: Path
    sessions_db_path: Path
    modelo_principal: str
    modelo_especialistas: str
    provedor: str
    host: str
    port: int


def _env(nome: str, padrao: str | Path) -> str:
    """Variável de ambiente; vazia (como no .env.example) conta como ausente."""
    return os.getenv(nome) or str(padrao)


def get_settings() -> Settings:
    var_dir = Path(_env("AURORA_VAR_DIR", PROJECT_ROOT / "var"))
    # Provedor exigido pelo desafio: Gemini (Google AI Studio). "openai" é um
    # modo alternativo opcional (via LiteLLM) usado só para validação local.
    provedor = _env("AURORA_PROVEDOR", "gemini").lower()
    modelo = _env(
        "AURORA_MODELO",
        "openai/gpt-4.1-mini" if provedor == "openai" else "gemini-3.6-flash",
    )
    return Settings(
        dados_dir=Path(_env("AURORA_DADOS_DIR", DADOS_DIR)),
        db_path=Path(_env("AURORA_DB_PATH", var_dir / "condominio.db")),
        sessions_db_path=Path(
            _env("AURORA_SESSOES_DB_PATH", var_dir / "sessoes.db")
        ),
        modelo_principal=_env("AURORA_MODELO_PRINCIPAL", modelo),
        modelo_especialistas=_env("AURORA_MODELO_ESPECIALISTAS", modelo),
        provedor=provedor,
        host=_env("AURORA_HOST", "0.0.0.0"),
        port=int(_env("AURORA_PORT", "8000")),
    )
