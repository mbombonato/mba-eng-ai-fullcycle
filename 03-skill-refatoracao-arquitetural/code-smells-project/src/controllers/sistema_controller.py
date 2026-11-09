"""Endpoints de sistema: index, health, relatório e administração."""
import logging

from flask import jsonify

from ..database.schema import reset_db

logger = logging.getLogger(__name__)


class SistemaController:
    def __init__(self, settings, connection_provider, produto_model, usuario_model, pedido_model, relatorio_service):
        self._settings = settings
        self._conn = connection_provider
        self._produtos = produto_model
        self._usuarios = usuario_model
        self._pedidos = pedido_model
        self._relatorios = relatorio_service

    def index(self):
        return jsonify({
            "mensagem": "Bem-vindo à API da Loja",
            "versao": self._settings.app_version,
            "endpoints": {
                "produtos": "/produtos",
                "usuarios": "/usuarios",
                "pedidos": "/pedidos",
                "login": "/login",
                "relatorios": "/relatorios/vendas",
                "health": "/health",
            },
        })

    def health(self):
        return jsonify({
            "status": "ok",
            "database": "connected",
            "counts": {
                "produtos": self._produtos.count(),
                "usuarios": self._usuarios.count(),
                "pedidos": self._pedidos.count(),
            },
            "versao": self._settings.app_version,
        }), 200

    def relatorio_vendas(self):
        return jsonify({"dados": self._relatorios.vendas(), "sucesso": True}), 200

    def reset_database(self):
        reset_db(self._conn())
        logger.warning("Banco de dados resetado via endpoint administrativo")
        return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200
