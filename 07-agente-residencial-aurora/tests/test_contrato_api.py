"""Contrato da API: caminhos, campos e códigos de status."""

from __future__ import annotations


def test_criar_sessao_201(api):
    r = api.post("/sessoes", json={"apartamento": "101"})
    assert r.status_code == 201
    assert set(r.json()) == {"session_id"}


def test_rotas_de_sessao_inexistente_404(api):
    assert api.get("/sessoes/sessao-inexistente/eventos").status_code == 404
    assert api.post("/sessoes/x/mensagens", json={"texto": "oi"}).status_code == 404
    assert (
        api.post("/sessoes/x/confirmacoes", json={"id": "a", "confirmado": True}).status_code
        == 404
    )


def test_formato_da_resposta_de_mensagem(api):
    sid = api.post("/sessoes", json={"apartamento": "101"}).json()["session_id"]
    body = api.post(f"/sessoes/{sid}/mensagens", json={"texto": "Reserve o salão de festas para 2030-04-20"}).json()
    assert set(body) == {"resposta", "confirmacoes_pendentes"}
    assert isinstance(body["resposta"], str)
    [p] = body["confirmacoes_pendentes"]
    assert {"id", "acao", "detalhes"} <= set(p)
    assert p["detalhes"]["area"] == "salao-de-festas" and p["detalhes"]["data"] == "2030-04-20"
    r = api.post(f"/sessoes/{sid}/confirmacoes", json={"id": p["id"], "confirmado": True})
    assert r.status_code == 200
    assert set(r.json()) == {"resposta", "confirmacoes_pendentes"}
    assert r.json()["confirmacoes_pendentes"] == []


def test_confirmacao_inexistente_409(api):
    sid = api.post("/sessoes", json={"apartamento": "101"}).json()["session_id"]
    r = api.post(f"/sessoes/{sid}/confirmacoes", json={"id": "id-inexistente", "confirmado": True})
    assert r.status_code == 409


def test_eventos_lista_em_ordem(api):
    sid = api.post("/sessoes", json={"apartamento": "101"}).json()["session_id"]
    assert api.get(f"/sessoes/{sid}/eventos").json() == []
    api.post(f"/sessoes/{sid}/mensagens", json={"texto": "Quais são as minhas reservas?"})
    eventos = api.get(f"/sessoes/{sid}/eventos").json()
    assert eventos[0]["author"] == "user"
    assert eventos[0]["content"]["parts"][0]["text"] == "Quais são as minhas reservas?"
    ts = [e["timestamp"] for e in eventos]
    assert ts == sorted(ts)


def test_rotas_de_verificacao_dados_iniciais(api):
    assert api.get("/apartamentos/101/reservas").json() == [
        {"codigo": "RSV-1377", "area": "quadra", "data": "2030-03-09"}
    ]
    assert api.get("/apartamentos/302/visitantes").json() == [
        {"nome": "Marina Duarte", "data": "2030-03-16"}
    ]
    assert api.get("/apartamentos/102/reservas").json() == []
