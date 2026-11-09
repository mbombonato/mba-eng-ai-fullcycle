import logging

from flask import jsonify, request

from ..middlewares.error_handler import NotFoundError
from ..views.serializers import produto_view
from .validators import parse_optional_float, validate_produto

logger = logging.getLogger(__name__)


class ProdutoController:
    def __init__(self, produto_model):
        self._produtos = produto_model

    def _get_or_404(self, produto_id):
        produto = self._produtos.find_by_id(produto_id)
        if produto is None:
            raise NotFoundError("Produto não encontrado")
        return produto

    def listar(self):
        produtos = [produto_view(p) for p in self._produtos.list_all()]
        return jsonify({"dados": produtos, "sucesso": True}), 200

    def buscar(self, id):  # noqa: A002 — nome do parâmetro definido pela rota <int:id>
        return jsonify({"dados": produto_view(self._get_or_404(id)), "sucesso": True}), 200

    def pesquisar(self):
        resultados = self._produtos.search(
            termo=request.args.get("q", ""),
            categoria=request.args.get("categoria") or None,
            preco_min=parse_optional_float(request.args.get("preco_min"), "preco_min"),
            preco_max=parse_optional_float(request.args.get("preco_max"), "preco_max"),
        )
        dados = [produto_view(p) for p in resultados]
        return jsonify({"dados": dados, "total": len(dados), "sucesso": True}), 200

    def criar(self):
        produto = validate_produto(request.get_json(silent=True))
        produto_id = self._produtos.create(**produto)
        logger.info("Produto criado id=%s", produto_id)
        return jsonify({"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}), 201

    def atualizar(self, id):  # noqa: A002
        self._get_or_404(id)
        produto = validate_produto(request.get_json(silent=True))
        self._produtos.update(id, **produto)
        return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200

    def deletar(self, id):  # noqa: A002
        self._get_or_404(id)
        self._produtos.delete(id)
        logger.info("Produto deletado id=%s", id)
        return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
