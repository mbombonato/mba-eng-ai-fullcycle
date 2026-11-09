"""F3: POST /reports/topics.

Na main a F3 passou a Asynchronous Request-Reply (ADR 0004): 202 + Location + Retry-After,
status em /reports/topics/status/{id} e 303 para o resultado. O relatório é o mesmo fixado
na v1-coupled. As validações de entrada continuam síncronas (422 antes do 202).
"""

from conftest import golden, wait_report

ROUTE = "/reports/topics"


def request_report(client, start, end):
    response = client.post(ROUTE, json={"start": start, "end": end})
    assert response.status_code == 202
    assert response.headers["location"].startswith("/reports/topics/status/")
    assert int(response.headers["retry-after"]) > 0
    final = wait_report(client, response.headers["location"])
    assert final.status_code == 303, final.text
    result = client.get(final.headers["location"])
    assert result.status_code == 200
    return result.json()


def test_two_day_report_is_fixed(client):
    assert request_report(client, "2026-08-01", "2026-08-02") == golden("f3_report_2026-08-01_2026-08-02.json")


def test_period_without_tickets(client):
    assert request_report(client, "2026-09-01", "2026-09-30") == {
        "start": "2026-09-01", "end": "2026-09-30", "total_tickets": 0, "topics": []}


def test_start_after_end_is_rejected(client):
    response = client.post(ROUTE, json={"start": "2026-08-31", "end": "2026-08-01"})

    assert response.status_code == 422
    assert response.json() == {"detail": "A data inicial é posterior à data final"}


def test_invalid_date_is_rejected(client):
    response = client.post(ROUTE, json={"start": "2026-02-30", "end": "2026-08-01"})

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "start"]


def test_unknown_report_is_404(client):
    assert client.get("/reports/topics/status/naoexiste").status_code == 404
    assert client.get("/reports/topics/naoexiste").status_code == 404
