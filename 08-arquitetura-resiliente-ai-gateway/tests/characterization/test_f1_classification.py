"""F1: POST /tickets/classification (síncrono na v1)."""

import pytest

from conftest import TICKET_42

ROUTE = "/tickets/classification"


def test_classifies_late_delivery_as_high_priority(client):
    response = client.post(ROUTE, json=TICKET_42)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"ticket_id": "TK-00042", "category": "delivery", "priority": "high"}


@pytest.mark.parametrize(
    "text, category, priority",
    [
        ("Fui cobrado duas vezes no cartão pelo mesmo pedido", "payment", "high"),
        ("Gostaria de saber como trocar o tamanho da camiseta", "exchange_return", "low"),
        ("A cafeteira elétrica parou de funcionar depois de uma semana", "product_defect", "medium"),
        ("Esqueci a senha da minha conta", "other", "medium"),
    ],
)
def test_classification_values(client, text, category, priority):
    response = client.post(ROUTE, json={"ticket_id": "TK-1", "text": text})

    assert response.status_code == 200
    assert response.json() == {"ticket_id": "TK-1", "category": category, "priority": priority}


def test_missing_text_is_rejected(client):
    response = client.post(ROUTE, json={"ticket_id": "TK-00042"})

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "missing"
    assert error["loc"] == ["body", "text"]


def test_empty_ticket_id_is_rejected(client):
    response = client.post(ROUTE, json={"ticket_id": "", "text": "Meu pedido não chegou"})

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "string_too_short"
    assert error["loc"] == ["body", "ticket_id"]
