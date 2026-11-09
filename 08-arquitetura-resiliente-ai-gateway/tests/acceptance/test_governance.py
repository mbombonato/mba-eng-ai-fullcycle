"""Governança: recusa por limite de requisições e por orçamento, sem chegar ao provider.

Aperta temporariamente os limites das chaves da aplicação pela API de administração do
gateway e os restaura no fim (os valores de referência estão em gateway/keys.json).
"""

import json
from pathlib import Path

import pytest

from conftest import TICKET, run_report

KEYS = {k["key_alias"]: k for k in json.loads(
    (Path(__file__).resolve().parents[2] / "gateway" / "keys.json").read_text(encoding="utf-8"))}
KEY_VALUES = {"helpdesk-realtime": "sk-helpdesk-realtime-0001", "helpdesk-reports": "sk-helpdesk-reports-0001"}


@pytest.fixture
def tighten(gateway_admin):
    changed = []

    def apply(alias, **limits):
        changed.append(alias)
        response = gateway_admin.post("/key/update", json={"key": KEY_VALUES[alias], **limits})
        response.raise_for_status()

    yield apply
    for alias in changed:
        spec = KEYS[alias]
        gateway_admin.post("/key/update", json={"key": KEY_VALUES[alias], "rpm_limit": spec["rpm_limit"],
                                                "max_budget": spec["max_budget"]}).raise_for_status()


def test_rate_limit_refuses_before_reaching_provider(client, provider, tighten):
    tighten("helpdesk-realtime", rpm_limit=1)

    first = client.post("/tickets/classification", json=TICKET)
    calls_before = len(provider.calls())
    refused = client.post("/tickets/classification", json=TICKET)

    assert first.status_code == 200
    assert refused.status_code == 429
    assert "limite de requisições" in refused.json()["detail"]
    assert len(provider.calls()) == calls_before


def test_budget_refuses_before_reaching_provider(client, provider, tighten, gateway_admin):
    spend = gateway_admin.get("/key/info", params={"key": KEY_VALUES["helpdesk-reports"]}).json()["info"]["spend"]
    tighten("helpdesk-reports", max_budget=spend)  # gasto atual == orçamento: estourado

    calls_before = len(provider.calls())
    _, state, body, _ = run_report(client)

    assert state == "failed"
    assert "orçamento" in body["reason"]
    assert len(provider.calls()) == calls_before
