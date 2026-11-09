"""Regras de negócio de pedidos."""
from collections import Counter

from ..config.constants import STATUS_PEDIDO
from ..middlewares.error_handler import NotFoundError, ValidationError
from ..models.pedido_model import EstoqueConcorrenteError


class PedidoService:
    def __init__(self, pedido_model, produto_model, usuario_model, notificacao_service):
        self._pedidos = pedido_model
        self._produtos = produto_model
        self._usuarios = usuario_model
        self._notificacoes = notificacao_service

    def criar(self, usuario_id, itens):
        """`itens`: lista já validada de {"produto_id": int, "quantidade": int > 0}."""
        if self._usuarios.find_by_id(usuario_id) is None:
            raise NotFoundError("Usuário não encontrado")

        produtos = self._produtos.find_by_ids(i["produto_id"] for i in itens)
        quantidade_por_produto = Counter()
        for item in itens:
            if item["produto_id"] not in produtos:
                raise ValidationError(f"Produto {item['produto_id']} não encontrado")
            quantidade_por_produto[item["produto_id"]] += item["quantidade"]

        for produto_id, quantidade in quantidade_por_produto.items():
            produto = produtos[produto_id]
            if produto["estoque"] < quantidade:
                raise ValidationError(f"Estoque insuficiente para {produto['nome']}")

        linhas = [
            {**item, "preco_unitario": produtos[item["produto_id"]]["preco"]} for item in itens
        ]
        total = sum(linha["preco_unitario"] * linha["quantidade"] for linha in linhas)
        try:
            pedido_id = self._pedidos.create_with_items(usuario_id, total, linhas)
        except EstoqueConcorrenteError as exc:
            nome = produtos[exc.args[0]]["nome"]
            raise ValidationError(f"Estoque insuficiente para {nome}") from exc

        self._notificacoes.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}

    def listar_todos(self):
        return self._pedidos.list_all()

    def listar_por_usuario(self, usuario_id):
        return self._pedidos.list_by_usuario(usuario_id)

    def atualizar_status(self, pedido_id, status):
        if status not in STATUS_PEDIDO:
            raise ValidationError("Status inválido")
        if not self._pedidos.exists(pedido_id):
            raise NotFoundError("Pedido não encontrado")
        self._pedidos.update_status(pedido_id, status)
        self._notificacoes.status_alterado(pedido_id, status)
