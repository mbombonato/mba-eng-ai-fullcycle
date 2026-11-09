"""Requisitos de experiência no modo normal, medidos pela borda."""

import time

from conftest import PRIMARY, TICKET, run_report, stream_suggestion


def test_f1_completes_within_3s(client, provider):
    start = time.monotonic()
    response = client.post("/tickets/classification", json=TICKET)
    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert response.json() == {"ticket_id": "TK-00042", "category": "delivery", "priority": "high"}
    assert elapsed <= 3


def test_f2_first_chunk_within_1_5s_and_before_half_of_total(client, provider):
    status, events, first, total = stream_suggestion(client)

    assert status == 200
    assert first <= 1.5
    assert first < total / 2
    assert events[-1] == ("end", {"ticket_id": "TK-00042"})


def test_f3_month_is_accepted_within_1s_and_covers_5000_tickets(client, provider):
    post_seconds, state, body, _ = run_report(client, "2026-08-01", "2026-08-31")

    assert post_seconds <= 1
    assert state == "done"
    assert body["total_tickets"] == 5000
    assert sum(t["count"] for t in body["topics"]) == 5000
    topics_calls = [c for c in provider.calls("topics") if c["status"] == 200]
    assert len(topics_calls) == 34
    assert {c["model"] for c in topics_calls} == {PRIMARY["topics"]}
