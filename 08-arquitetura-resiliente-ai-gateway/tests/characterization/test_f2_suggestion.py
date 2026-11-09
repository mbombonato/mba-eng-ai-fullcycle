"""F2: POST /tickets/reply-suggestion (síncrono na v1: o texto inteiro no corpo JSON)."""

from conftest import TICKET_42, golden

ROUTE = "/tickets/reply-suggestion"


def test_suggestion_text_is_fixed(client):
    response = client.post(ROUTE, json=TICKET_42)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"ticket_id": "TK-00042", **golden("f2_suggestion_tk00042.json")}


def test_missing_ticket_id_is_rejected(client):
    response = client.post(ROUTE, json={"text": "Meu pedido não chegou"})

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "missing"
    assert error["loc"] == ["body", "ticket_id"]
