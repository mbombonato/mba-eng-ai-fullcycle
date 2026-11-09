"""Configuração da aplicação — único ponto que lê variáveis de ambiente."""
import os
import secrets
from dataclasses import dataclass, field

from dotenv import load_dotenv


def _env_bool(env, name):
    return env.get(name, "0").strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    secret_key: str
    database_url: str = "sqlite:///tasks.db"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 5000
    cors_origins: list = field(default_factory=lambda: ["*"])
    token_max_age_seconds: int = 3600

    @classmethod
    def from_env(cls, env=None):
        if env is None:
            load_dotenv()
            env = os.environ
        return cls(
            # Sem SECRET_KEY, gera uma chave efêmera: tokens emitidos não sobrevivem a restart.
            secret_key=env.get("SECRET_KEY") or secrets.token_hex(32),
            database_url=env.get("DATABASE_URL", "sqlite:///tasks.db"),
            debug=_env_bool(env, "FLASK_DEBUG"),
            host=env.get("HOST", "127.0.0.1"),
            port=int(env.get("PORT", "5000")),
            cors_origins=[o.strip() for o in env.get("CORS_ORIGINS", "*").split(",") if o.strip()],
            token_max_age_seconds=int(env.get("TOKEN_MAX_AGE_SECONDS", "3600")),
        )
