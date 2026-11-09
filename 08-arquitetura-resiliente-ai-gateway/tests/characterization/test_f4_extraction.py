"""F4: POST /tickets/extraction (síncrono)."""

ROUTE = "/tickets/extraction"


def test_extracts_order_number_and_product_ignoring_invoice_number(client):
    ticket = {
        "ticket_id": "TK-04171",
        "text": "Tenho aqui a nota fiscal 702732. Fiz o pix de o smartwatch e o pagamento consta "
                "como pendente. Referente ao pedido #364733. Prefiro contato por e-mail.",
    }
    response = client.post(ROUTE, json=ticket)

    assert response.status_code == 200
    assert response.json() == {"ticket_id": "TK-04171", "order_number": "#364733", "product": "smartwatch"}


def test_order_number_without_hash(client):
    ticket = {"ticket_id": "TK-00159",
              "text": "O smartwatch veio quebrado na caixa, pedido 789719. Fico no aguardo de uma solução."}
    response = client.post(ROUTE, json=ticket)

    assert response.status_code == 200
    assert response.json() == {"ticket_id": "TK-00159", "order_number": "#789719", "product": "smartwatch"}


def test_ticket_without_order_returns_nulls(client):
    response = client.post(ROUTE, json={"ticket_id": "TK-9", "text": "Esqueci a senha da minha conta"})

    assert response.status_code == 200
    assert response.json() == {"ticket_id": "TK-9", "order_number": None, "product": None}


def test_empty_text_is_rejected(client):
    response = client.post(ROUTE, json={"ticket_id": "TK-9", "text": ""})

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "string_too_short"
    assert error["loc"] == ["body", "text"]
