"""Conexão SQLite por requisição (sem estado global compartilhado entre threads)."""
import sqlite3

from flask import current_app, g


def connect(database_path):
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_connection():
    """Retorna a conexão da requisição atual, abrindo-a sob demanda."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_connection(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app):
    app.teardown_appcontext(close_connection)
