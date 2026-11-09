"""Configuração comum da suíte de caracterização.

A suíte fala só HTTP com a borda (http://localhost:8000 por padrão) e usa o
endpoint /admin/reset do provider simulado para começar de um estado limpo.
"""

import json
import os
import time
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


def sse_events(response: httpx.Response) -> list[tuple[str, dict]]:
    """Lê um stream text/event-stream e devolve [(evento, dados)]; evento padrão = "message"."""
    events, event, data = [], "message", []
    for line in response.iter_lines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].strip())
        elif line == "" and data:
            events.append((event, json.loads("\n".join(data))))
            event, data = "message", []
    if data:
        events.append((event, json.loads("\n".join(data))))
    return events


def wait_report(client: httpx.Client, status_url: str, timeout: float = 90) -> httpx.Response:
    """Consulta a URL de status até o 303 (ou failed) e devolve a última resposta."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(status_url)
        if response.status_code != 200 or response.json()["state"] == "failed":
            return response
        time.sleep(1)
    raise AssertionError(f"relatório não terminou em {timeout} s")


@pytest.fixture(scope="session", autouse=True)
def provider_in_normal_mode():
    httpx.post(f"{PROVIDER_URL}/admin/reset", timeout=10).raise_for_status()
    yield


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=120) as c:
        yield c
