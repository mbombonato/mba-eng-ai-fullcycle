"""Configuração comum da suíte de caracterização.

A suíte fala só HTTP com a borda (http://localhost:8000 por padrão) e usa o
endpoint /admin/reset do provider simulado para começar de um estado limpo.
"""

import json
import os
from pathlib import Path

import httpx
import pytest

BASE_URL = os.environ.get("HELPDESK_URL", "http://localhost:8000")
PROVIDER_URL = os.environ.get("PROVIDER_URL", "http://localhost:8090")
GOLDEN_DIR = Path(__file__).parent / "golden"

TICKET_42 = {
    "ticket_id": "TK-00042",
    "text": "Meu pedido #481516 não chegou e já passou do prazo, urgente",
}


def golden(name: str):
    return json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="session", autouse=True)
def provider_in_normal_mode():
    httpx.post(f"{PROVIDER_URL}/admin/reset", timeout=10).raise_for_status()
    yield


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=120) as c:
        yield c
