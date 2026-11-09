"""F2: POST /tickets/reply-suggestion.

Na main a F2 passou a streaming (SSE, ADR 0004): o texto é o mesmo fixado na v1-coupled,
agora entregue em eventos `data: {"chunk": ...}` e encerrado por `event: end`.
"""

from conftest import TICKET_42, golden, sse_events

ROUTE = "/tickets/reply-suggestion"


def test_suggestion_is_streamed_with_the_same_text(client):
    with client.stream("POST", ROUTE, json=TICKET_42) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        events = sse_events(response)

    chunks = [data["chunk"] for event, data in events if event == "message"]
    assert len(chunks) > 1
    assert "".join(chunks) == golden("f2_suggestion_tk00042.json")["suggestion"]
    assert events[-1] == ("end", {"ticket_id": "TK-00042"})


def test_missing_ticket_id_is_rejected(client):
    response = client.post(ROUTE, json={"text": "Meu pedido não chegou"})

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "missing"
    assert error["loc"] == ["body", "ticket_id"]
