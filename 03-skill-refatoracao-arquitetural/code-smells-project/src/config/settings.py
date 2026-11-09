"""Configuração da aplicação — único ponto que lê variáveis de ambiente."""
import os
import secrets
from dataclasses import dataclass, field


def _env_bool(env, name, default=False):
    return env.get(name, "1" if default else "0").strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    secret_key: str
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 5000
    database_path: str = "loja.db"
    admin_token: str = ""
    cors_origins: list = field(default_factory=lambda: ["*"])
    app_version: str = "1.0.0"

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        origins = env.get("CORS_ORIGINS", "*")
        return cls(
            # Sem SECRET_KEY definida, gera uma chave efêmera (sessões não sobrevivem a restart).
            secret_key=env.get("SECRET_KEY") or secrets.token_hex(32),
            debug=_env_bool(env, "FLASK_DEBUG"),
            host=env.get("HOST", "127.0.0.1"),
            port=int(env.get("PORT", "5000")),
            database_path=env.get("DATABASE_PATH", "loja.db"),
            admin_token=env.get("ADMIN_TOKEN", ""),
            cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
        )
