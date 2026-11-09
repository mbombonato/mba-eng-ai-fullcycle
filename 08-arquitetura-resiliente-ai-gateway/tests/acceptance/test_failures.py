"""Falhas do provider: fallback técnico, modelo fraco, timeout, stream interrompido."""

import time

import pytest

from conftest import (EXTRACT_TICKET, FALLBACK, MAX_ATTEMPTS_PER_DESTINATION, PRIMARY, TICKET,
                      run_report, stream_suggestion)

PROVIDER_OF = {"gpt-fake-large": "openai", "claude-fake-large": "anthropic"}


def assert_primary_then_fallback(calls, task):
    primary = [c for c in calls if c["model"] == PRIMARY[task]]
    fallback = [c for c in calls if c["model"] == FALLBACK[task]]
    assert 1 <= len(primary) <= MAX_ATTEMPTS_PER_DESTINATION
    assert all(c["status"] == 500 for c in primary)
    assert fallback and fallback[-1]["status"] == 200
    assert calls.index(primary[-1]) < calls.index(fallback[0])


@pytest.mark.parametrize("task", ["classify", "extract"])
def test_sync_feature_falls_back_to_other_provider(client, provider, task):
    provider.fail(PROVIDER_OF[PRIMARY[task]], "error_500")
    route = {"classify": "/tickets/classification", "extract": "/tickets/extraction"}[task]
    body = TICKET if task == "classify" else EXTRACT_TICKET

    response = client.post(route, json=body)

    assert response.status_code == 200
    assert_primary_then_fallback(provider.calls(task), task)


def test_f2_falls_back_to_other_provider(client, provider):
    provider.fail("anthropic", "error_500")

    status, events, _, _ = stream_suggestion(client)

    assert status == 200 and events[-1][0] == "end"
    assert_primary_then_fallback(provider.calls("suggest"), "suggest")


def test_f3_falls_back_to_other_provider(client, provider):
    provider.fail("anthropic", "error_500")

    _, state, body, _ = run_report(client)

    assert state == "done" and body["total_tickets"] == 274
    calls = provider.calls("topics")
    assert {c["model"] for c in calls if c["status"] == 200} == {FALLBACK["topics"]}
    assert len([c for c in calls if c["model"] == PRIMARY["topics"]]) <= 2 * MAX_ATTEMPTS_PER_DESTINATION


class TestWithoutLargeModels:
    """Os dois large em error_500: cada feature faz o que a tabela de fallback declara."""

    @pytest.fixture(autouse=True)
    def no_large(self, provider):
        provider.fail("openai", "error_500", "gpt-fake-large")
        provider.fail("anthropic", "error_500", "claude-fake-large")

    def test_f1_answers_with_mini(self, client, provider):
        response = client.post("/tickets/classification", json=TICKET)

        assert response.status_code == 200
        assert response.json() == {"ticket_id": "TK-00042", "category": "delivery", "priority": "high"}
        assert provider.calls("classify")[-1]["model"] == "gpt-fake-mini"

    def test_f2_streams_mini_suggestion(self, client, provider):
        status, events, _, _ = stream_suggestion(client)

        assert status == 200 and events[-1][0] == "end"
        assert provider.calls("suggest")[-1]["model"] == "claude-fake-mini"

    def test_f3_report_built_with_mini(self, client, provider):
        _, state, body, _ = run_report(client)

        assert state == "done" and body["total_tickets"] == 274
        assert {c["model"] for c in provider.calls("topics") if c["status"] == 200} == {"claude-fake-mini"}

    def test_f4_fails_explicitly_without_mini(self, client, provider):
        response = client.post("/tickets/extraction", json=EXTRACT_TICKET)

        assert response.status_code == 503
        assert "order-extraction" in response.json()["detail"]
        models = {c["model"] for c in provider.calls("extract")}
        assert models == {"gpt-fake-large", "claude-fake-large"}  # nenhum mini foi chamado


def test_f3_fails_visibly_within_60s_with_both_providers_down(client, provider):
    provider.fail("openai", "error_500")
    provider.fail("anthropic", "error_500")

    _, state, body, elapsed = run_report(client, "2026-08-01", "2026-08-31", timeout=60)

    assert state == "failed"
    assert body["reason"]
    assert elapsed <= 60


def test_f1_answers_within_15s_with_primary_in_timeout(client, provider):
    provider.fail("openai", "timeout")

    start = time.monotonic()
    response = client.post("/tickets/classification", json=TICKET)
    elapsed = time.monotonic() - start

    assert response.status_code in (200, 503)
    assert response.status_code != 504
    assert elapsed <= 15


def test_f2_midstream_error_reaches_client_as_error_event(client, provider):
    provider.fail("anthropic", "midstream_error")

    status, events, _, _ = stream_suggestion(client)

    assert status == 200
    assert any(e == "message" for e, _ in events)
    assert events[-1] == ("error", {"ticket_id": "TK-00042", "message": "A geração foi interrompida"})
