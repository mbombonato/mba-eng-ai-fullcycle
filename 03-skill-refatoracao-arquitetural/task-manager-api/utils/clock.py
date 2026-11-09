"""Relógio da aplicação: substitui o deprecated datetime.utcnow()."""
from datetime import datetime, timezone


def utcnow():
    """UTC sem tzinfo, compatível com as colunas DateTime (naive) já existentes."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
