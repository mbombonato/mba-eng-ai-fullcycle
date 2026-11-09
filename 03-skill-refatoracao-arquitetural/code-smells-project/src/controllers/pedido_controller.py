from flask import jsonify, request

from ..views.serializers import pedido_view
from .validators import validate_pedido, validate_status


class PedidoController:
    def __init__(self, pedido_service):
        self._service = pedido_service

    def criar(self):
        usuario_id, itens = validate_pedido(request.get_json(silent=True))
        resultado = self._service.criar(usuario_id, itens)
        return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}), 201

    def listar_todos(self):
        pedidos = [pedido_view(p, itens) for p, itens in self._service.listar_todos()]
        return jsonify({"dados": pedidos, "sucesso": True}), 200

    def listar_por_usuario(self, usuario_id):
        pedidos = [pedido_view(p, itens) for p, itens in self._service.listar_por_usuario(usuario_id)]
        return jsonify({"dados": pedidos, "sucesso": True}), 200

    def atualizar_status(self, pedido_id):
        self._service.atualizar_status(pedido_id, validate_status(request.get_json(silent=True)))
        return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
