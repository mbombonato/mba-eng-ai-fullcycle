"""Acesso a dados de usuários e verificação de credenciais."""
import hmac

from werkzeug.security import check_password_hash, generate_password_hash

from ..config.constants import TIPO_USUARIO_PADRAO

USUARIO_COLUMNS = "id, nome, email, tipo, criado_em"
_HASH_PREFIXES = ("scrypt:", "pbkdf2:")


class UsuarioModel:
    def __init__(self, connection_provider):
        self._conn = connection_provider

    def list_all(self):
        return self._conn().execute(f"SELECT {USUARIO_COLUMNS} FROM usuarios").fetchall()

    def find_by_id(self, usuario_id):
        return self._conn().execute(
            f"SELECT {USUARIO_COLUMNS} FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()

    def find_by_email(self, email):
        return self._conn().execute(
            f"SELECT {USUARIO_COLUMNS} FROM usuarios WHERE email = ?", (email,)
        ).fetchone()

    def create(self, nome, email, senha, tipo=TIPO_USUARIO_PADRAO):
        conn = self._conn()
        with conn:
            cursor = conn.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, generate_password_hash(senha), tipo),
            )
        return cursor.lastrowid

    def authenticate(self, email, senha):
        """Retorna o usuário se a senha conferir; migra senhas legadas em texto puro para hash."""
        conn = self._conn()
        row = conn.execute("SELECT id, senha FROM usuarios WHERE email = ?", (email,)).fetchone()
        if row is None or not row["senha"]:
            return None
        stored = row["senha"]
        if stored.startswith(_HASH_PREFIXES):
            valid = check_password_hash(stored, senha)
        else:  # registro legado (texto puro) criado pela versão antiga
            valid = hmac.compare_digest(stored.encode(), senha.encode())
            if valid:
                with conn:
                    conn.execute(
                        "UPDATE usuarios SET senha = ? WHERE id = ?", (generate_password_hash(senha), row["id"])
                    )
        return self.find_by_id(row["id"]) if valid else None

    def count(self):
        return self._conn().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
