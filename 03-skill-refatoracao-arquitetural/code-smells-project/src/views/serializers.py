"""Views/presenters: definem exatamente quais campos saem na resposta (whitelist)."""

PRODUTO_FIELDS = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")
USUARIO_FIELDS = ("id", "nome", "email", "tipo", "criado_em")  # nunca inclui "senha"
LOGIN_FIELDS = ("id", "nome", "email", "tipo")
PEDIDO_FIELDS = ("id", "usuario_id", "status", "total", "criado_em")


def _pick(row, fields):
    return {field: row[field] for field in fields}


def produto_view(row):
    return _pick(row, PRODUTO_FIELDS)


def usuario_view(row):
    return _pick(row, USUARIO_FIELDS)


def login_view(row):
    return _pick(row, LOGIN_FIELDS)


def pedido_view(pedido, itens):
    data = _pick(pedido, PEDIDO_FIELDS)
    data["itens"] = [
        {
            "produto_id": item["produto_id"],
            "produto_nome": item["produto_nome"] if item["produto_nome"] is not None else "Desconhecido",
            "quantidade": item["quantidade"],
            "preco_unitario": item["preco_unitario"],
        }
        for item in itens
    ]
    return data
