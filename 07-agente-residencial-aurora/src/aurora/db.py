"""Armazenamento dos dados do condomínio em SQLite.

Os arquivos de ``dados/`` são só o estado inicial (lidos pela restauração).
Todas as mudanças feitas pelo assistente ficam em ``var/condominio.db``.

Garantia 5 (dois moradores, uma reserva): a exclusividade de uma área por
data é garantida pelo índice único parcial ``ux_reservas_area_data_ativa``.
O SQLite recusa a gravação de uma segunda reserva ativa para a mesma área e
data no instante do INSERT, independentemente de qualquer conferência feita
antes. A gravação ainda roda dentro de ``BEGIN IMMEDIATE`` (trava de escrita),
mas quem decide é o índice.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS apartamentos (
    numero  TEXT PRIMARY KEY,
    morador TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS areas (
    id   TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    taxa REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS reservas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo         TEXT NOT NULL UNIQUE,
    apartamento    TEXT NOT NULL,
    area           TEXT NOT NULL REFERENCES areas(id),
    data           TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'ativa'
                   CHECK (status IN ('ativa', 'cancelada')),
    confirmacao_id TEXT UNIQUE,
    criada_em      TEXT NOT NULL,
    cancelada_em   TEXT
);

-- Garantia 5: no máximo UMA reserva ativa por área e data, garantido pelo
-- próprio banco no instante da gravação.
CREATE UNIQUE INDEX IF NOT EXISTS ux_reservas_area_data_ativa
    ON reservas(area, data) WHERE status = 'ativa';

-- Regra 5: códigos nunca se repetem, nem de reservas canceladas
-- (o cancelamento só muda o status; a linha e o código permanecem).
CREATE TABLE IF NOT EXISTS codigos_emitidos (
    codigo TEXT PRIMARY KEY
);

-- Garantia 2: o apartamento de cada sessão, fixado na criação (POST /sessoes).
CREATE TABLE IF NOT EXISTS sessoes (
    session_id  TEXT PRIMARY KEY,
    apartamento TEXT NOT NULL,
    criada_em   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS visitantes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    apartamento    TEXT NOT NULL,
    nome           TEXT NOT NULL,
    data           TEXT NOT NULL,
    confirmacao_id TEXT UNIQUE,
    criado_em      TEXT NOT NULL
);
"""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos e com espaços simples (para comparar nomes)."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().replace("-", " ").split())


def validar_data(valor: str) -> str | None:
    """Devolve a data em AAAA-MM-DD ou ``None`` se for inválida."""
    try:
        return date.fromisoformat(str(valor).strip()).isoformat()
    except ValueError:
        return None


@dataclass(frozen=True)
class Area:
    id: str
    nome: str
    taxa: float

    @property
    def gera_cobranca(self) -> bool:
        return self.taxa > 0


@dataclass(frozen=True)
class Reserva:
    codigo: str
    apartamento: str
    area: str
    data: str


@dataclass(frozen=True)
class ResultadoReserva:
    status: str  # "criada" | "ocupada" | "ja_executada"
    reserva: Reserva | None = None


class CondominioRepository:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conectar() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)

    # ------------------------------------------------------------------ infra
    def _conectar(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def _leitura(self) -> Iterator[sqlite3.Connection]:
        conn = self._conectar()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _escrita(self) -> Iterator[sqlite3.Connection]:
        """Transação com trava de escrita (BEGIN IMMEDIATE)."""
        conn = self._conectar()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")
        finally:
            conn.close()

    # ------------------------------------------------------------ restauração
    def restaurar(self, dados_dir: Path) -> None:
        """Volta apartamentos, áreas, reservas e visitantes ao estado de ``dados/``."""
        ler = lambda nome: json.loads((dados_dir / nome).read_text("utf-8"))  # noqa: E731
        apartamentos = ler("apartamentos.json")
        areas = ler("areas.json")
        reservas = ler("reservas.json")
        visitantes = ler("visitantes.json")
        agora = _agora()
        with self._escrita() as conn:
            conn.execute("DELETE FROM reservas")
            conn.execute("DELETE FROM visitantes")
            conn.execute("DELETE FROM codigos_emitidos")
            conn.execute("DELETE FROM areas")
            conn.execute("DELETE FROM apartamentos")
            conn.executemany(
                "INSERT INTO apartamentos(numero, morador) VALUES (?, ?)",
                [(a["numero"], a["morador"]) for a in apartamentos],
            )
            conn.executemany(
                "INSERT INTO areas(id, nome, taxa) VALUES (?, ?, ?)",
                [(a["id"], a["nome"], float(a["taxa"])) for a in areas],
            )
            conn.executemany(
                "INSERT INTO reservas(codigo, apartamento, area, data, criada_em)"
                " VALUES (?, ?, ?, ?, ?)",
                [
                    (r["codigo"], r["apartamento"], r["area"], r["data"], agora)
                    for r in reservas
                ],
            )
            conn.executemany(
                "INSERT INTO codigos_emitidos(codigo) VALUES (?)",
                [(r["codigo"],) for r in reservas],
            )
            conn.executemany(
                "INSERT INTO visitantes(apartamento, nome, data, criado_em)"
                " VALUES (?, ?, ?, ?)",
                [(v["apartamento"], v["nome"], v["data"], agora) for v in visitantes],
            )

    def esta_vazio(self) -> bool:
        with self._leitura() as conn:
            return conn.execute("SELECT COUNT(*) FROM areas").fetchone()[0] == 0

    # ---------------------------------------------------------------- sessões
    def registrar_sessao(self, session_id: str, apartamento: str) -> None:
        with self._escrita() as conn:
            conn.execute(
                "INSERT INTO sessoes(session_id, apartamento, criada_em)"
                " VALUES (?, ?, ?)",
                (session_id, apartamento, _agora()),
            )

    def apagar_sessoes(self) -> None:
        with self._escrita() as conn:
            conn.execute("DELETE FROM sessoes")

    def apartamento_registrado(self, session_id: str) -> str | None:
        with self._leitura() as conn:
            row = conn.execute(
                "SELECT apartamento FROM sessoes WHERE session_id = ?", (session_id,)
            ).fetchone()
            return row["apartamento"] if row else None

    # ------------------------------------------------------------ consultas
    def apartamento_existe(self, numero: str) -> bool:
        with self._leitura() as conn:
            row = conn.execute(
                "SELECT 1 FROM apartamentos WHERE numero = ?", (numero,)
            ).fetchone()
            return row is not None

    def listar_areas(self) -> list[Area]:
        with self._leitura() as conn:
            rows = conn.execute("SELECT id, nome, taxa FROM areas ORDER BY nome")
            return [Area(r["id"], r["nome"], r["taxa"]) for r in rows]

    def resolver_area(self, valor: str) -> Area | None:
        """Aceita o id (``salao-de-festas``) ou o nome (``Salão de festas``)."""
        alvo = normalizar(valor or "")
        if not alvo:
            return None
        areas = self.listar_areas()
        for area in areas:
            if alvo in (normalizar(area.id), normalizar(area.nome)):
                return area
        candidatas = [
            a for a in areas if alvo in normalizar(a.nome) or normalizar(a.id) in alvo
        ]
        return candidatas[0] if len(candidatas) == 1 else None

    def reservas_do_apartamento(self, apartamento: str) -> list[Reserva]:
        with self._leitura() as conn:
            rows = conn.execute(
                "SELECT codigo, apartamento, area, data FROM reservas"
                " WHERE apartamento = ? AND status = 'ativa' ORDER BY data, id",
                (apartamento,),
            )
            return [Reserva(**dict(r)) for r in rows]

    def data_ocupada(self, area_id: str, data: str) -> bool:
        with self._leitura() as conn:
            row = conn.execute(
                "SELECT 1 FROM reservas WHERE area = ? AND data = ? AND status = 'ativa'",
                (area_id, data),
            ).fetchone()
            return row is not None

    def visitantes_do_apartamento(self, apartamento: str) -> list[dict]:
        with self._leitura() as conn:
            rows = conn.execute(
                "SELECT nome, data FROM visitantes WHERE apartamento = ?"
                " ORDER BY data, id",
                (apartamento,),
            )
            return [dict(r) for r in rows]

    # ------------------------------------------------------------- gravações
    def criar_reserva(
        self,
        apartamento: str,
        area_id: str,
        data: str,
        confirmacao_id: str | None = None,
    ) -> ResultadoReserva:
        """Grava a reserva. A exclusividade é decidida pelo índice único.

        ``confirmacao_id`` (o id da chamada de tool aprovada) também é único:
        a mesma aprovação nunca grava duas reservas.
        """
        with self._escrita() as conn:
            if confirmacao_id:
                existente = conn.execute(
                    "SELECT codigo, apartamento, area, data FROM reservas"
                    " WHERE confirmacao_id = ?",
                    (confirmacao_id,),
                ).fetchone()
                if existente:
                    return ResultadoReserva("ja_executada", Reserva(**dict(existente)))
            for _ in range(20):
                codigo = f"RSV-{secrets.token_hex(3).upper()}"
                try:
                    conn.execute(
                        "INSERT INTO codigos_emitidos(codigo) VALUES (?)", (codigo,)
                    )
                except sqlite3.IntegrityError:
                    continue  # código já emitido algum dia: sorteia outro
                break
            else:  # pragma: no cover - probabilidade desprezível
                raise RuntimeError("Não foi possível gerar um código de reserva único")
            try:
                conn.execute(
                    "INSERT INTO reservas(codigo, apartamento, area, data,"
                    " confirmacao_id, criada_em) VALUES (?, ?, ?, ?, ?, ?)",
                    (codigo, apartamento, area_id, data, confirmacao_id, _agora()),
                )
            except sqlite3.IntegrityError as exc:
                if "reservas.area" in str(exc) or "reservas.data" in str(exc):
                    # Outra reserva ativa já ocupa a área nesta data. O código
                    # sorteado continua registrado em codigos_emitidos e não
                    # será reutilizado; o restante da transação segue normal.
                    return ResultadoReserva("ocupada")
                raise
            return ResultadoReserva(
                "criada", Reserva(codigo, apartamento, area_id, data)
            )

    def cancelar_reserva(self, apartamento: str, codigo: str) -> Reserva | None:
        """Cancela apenas se a reserva ativa pertencer ao ``apartamento``."""
        with self._escrita() as conn:
            row = conn.execute(
                "SELECT codigo, apartamento, area, data FROM reservas"
                " WHERE codigo = ? AND apartamento = ? AND status = 'ativa'",
                (codigo, apartamento),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE reservas SET status = 'cancelada', cancelada_em = ?"
                " WHERE codigo = ? AND apartamento = ?",
                (_agora(), codigo, apartamento),
            )
            return Reserva(**dict(row))

    def autorizar_visitante(
        self,
        apartamento: str,
        nome: str,
        data: str,
        confirmacao_id: str | None = None,
    ) -> tuple[str, dict]:
        """Grava a autorização. Devolve (status, visitante)."""
        with self._escrita() as conn:
            if confirmacao_id:
                existente = conn.execute(
                    "SELECT nome, data FROM visitantes WHERE confirmacao_id = ?",
                    (confirmacao_id,),
                ).fetchone()
                if existente:
                    return "ja_executada", dict(existente)
            conn.execute(
                "INSERT INTO visitantes(apartamento, nome, data, confirmacao_id,"
                " criado_em) VALUES (?, ?, ?, ?, ?)",
                (apartamento, nome, data, confirmacao_id, _agora()),
            )
            return "autorizado", {"nome": nome, "data": data}
