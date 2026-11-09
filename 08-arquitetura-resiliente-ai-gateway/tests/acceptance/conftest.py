"""Cenários de aceite da main: tempos, falhas do provider, fallback e governança.

Cada teste coloca o provider simulado num modo de falha via /admin/failures, exercita a
feature pela borda e confere em /admin/calls para onde as chamadas foram de fato.
"""

import json
import os
import time

import httpx
import pytest

BASE_URL = os.environ.get("HELPDESK_URL", "http://localhost:8000")
PROVIDER_URL = os.environ.get("PROVIDER_URL", "http://localhost:8090")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:4000")
MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "sk-gateway-master-0001")

TICKET = {"ticket_id": "TK-00042", "text": "Meu pedido #481516 não chegou e já passou do prazo, urgente"}
EXTRACT_TICKET = {"ticket_id": "TK-04171",
                  "text": "Tenho aqui a nota fiscal 702732. Fiz o pix de o smartwatch e o pagamento consta "
                          "como pendente. Referente ao pedido #364733. Prefiro contato por e-mail."}
# Primário e fallback técnico de cada capacidade (gateway/config.yaml).
PRIMARY = {"classify": "gpt-fake-large", "suggest": "claude-fake-large",
           "topics": "claude-fake-large", "extract": "gpt-fake-large"}
FALLBACK = {"classify": "claude-fake-large", "suggest": "gpt-fake-large",
            "topics": "gpt-fake-large", "extract": "claude-fake-large"}
MAX_ATTEMPTS_PER_DESTINATION = 2


class Provider:
    def __init__(self):
        self.http = httpx.Client(base_url=PROVIDER_URL, timeout=10)

    def reset(self):
        self.http.post("/admin/reset").raise_for_status()

    def fail(self, provider, mode, model=None):
        body = {"provider": provider, "mode": mode} | ({"model": model} if model else {})
        self.http.post("/admin/failures", json=body).raise_for_status()

    def calls(self, task=None):
        items = list(reversed(self.http.get("/admin/calls", params={"last": 500}).json()))
        return [c for c in items if task is None or c["task"] == task]


@pytest.fixture
def provider():
    p = Provider()
    p.reset()
    yield p
    p.reset()


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=120) as c:
        yield c


@pytest.fixture(scope="session")
def gateway_admin():
    with httpx.Client(base_url=GATEWAY_URL, timeout=30,
                      headers={"Authorization": f"Bearer {MASTER_KEY}"}) as c:
        yield c


def stream_suggestion(client, ticket=TICKET):
    """Devolve (status, eventos, segundos até o primeiro trecho, segundos totais)."""
    start, first, events = time.monotonic(), None, []
    with client.stream("POST", "/tickets/reply-suggestion", json=ticket) as response:
        if response.status_code != 200:
            response.read()
            return response.status_code, response.json(), None, time.monotonic() - start
        event = "message"
        for line in response.iter_lines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:])
                if first is None and event == "message":
                    first = time.monotonic() - start
                events.append((event, data))
                event = "message"
    return 200, events, first, time.monotonic() - start


def run_report(client, start="2026-08-01", end="2026-08-02", timeout=90):
    """Pede o relatório e acompanha a URL de status. Devolve (segundos do POST, status final, corpo)."""
    t0 = time.monotonic()
    accepted = client.post("/reports/topics", json={"start": start, "end": end})
    post_seconds = time.monotonic() - t0
    assert accepted.status_code == 202, accepted.text
    status_url = accepted.headers["location"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = client.get(status_url)
        assert status.status_code != 504
        if status.status_code == 303:
            result = client.get(status.headers["location"])
            return post_seconds, "done", result.json(), time.monotonic() - t0
        if status.json()["state"] == "failed":
            return post_seconds, "failed", status.json(), time.monotonic() - t0
        time.sleep(1)
    raise AssertionError("relatório preso sem terminar")
