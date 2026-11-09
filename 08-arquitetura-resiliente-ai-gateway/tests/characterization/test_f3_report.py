"""F3: POST /reports/topics (síncrono na v1: o relatório inteiro no corpo da resposta).

A caracterização usa períodos curtos: o mês inteiro não termina antes dos 30 s da borda
na v1 (é uma das dores do diagnóstico), então ele não pode ser fixado aqui.
"""

from conftest import golden

ROUTE = "/reports/topics"


def test_two_day_report_is_fixed(client):
    response = client.post(ROUTE, json={"start": "2026-08-01", "end": "2026-08-02"})

    assert response.status_code == 200
    assert response.json() == golden("f3_report_2026-08-01_2026-08-02.json")


def test_period_without_tickets(client):
    response = client.post(ROUTE, json={"start": "2026-09-01", "end": "2026-09-30"})

    assert response.status_code == 200
    assert response.json() == {"start": "2026-09-01", "end": "2026-09-30", "total_tickets": 0, "topics": []}


def test_start_after_end_is_rejected(client):
    response = client.post(ROUTE, json={"start": "2026-08-31", "end": "2026-08-01"})

    assert response.status_code == 422
    assert response.json() == {"detail": "A data inicial é posterior à data final"}


def test_invalid_date_is_rejected(client):
    response = client.post(ROUTE, json={"start": "2026-02-30", "end": "2026-08-01"})

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "start"]
