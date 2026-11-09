from flask import jsonify, request

from ..middlewares.error_handler import ConflictError, NotFoundError, UnauthorizedError
from ..views.serializers import login_view, usuario_view
from .validators import validate_login, validate_novo_usuario


class UsuarioController:
    def __init__(self, usuario_model):
        self._usuarios = usuario_model

    def listar(self):
        usuarios = [usuario_view(u) for u in self._usuarios.list_all()]
        return jsonify({"dados": usuarios, "sucesso": True}), 200

    def buscar(self, id):  # noqa: A002 — nome do parâmetro definido pela rota <int:id>
        usuario = self._usuarios.find_by_id(id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")
        return jsonify({"dados": usuario_view(usuario), "sucesso": True}), 200

    def criar(self):
        dados = validate_novo_usuario(request.get_json(silent=True))
        if self._usuarios.find_by_email(dados["email"]) is not None:
            raise ConflictError("Email já cadastrado")
        usuario_id = self._usuarios.create(dados["nome"], dados["email"], dados["senha"])
        return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201

    def login(self):
        email, senha = validate_login(request.get_json(silent=True))
        usuario = self._usuarios.authenticate(email, senha)
        if usuario is None:
            raise UnauthorizedError("Email ou senha inválidos")
        return jsonify({"dados": login_view(usuario), "sucesso": True, "mensagem": "Login OK"}), 200
