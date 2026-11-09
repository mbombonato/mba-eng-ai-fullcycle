"""Validação de entrada — regras únicas reaproveitadas por create e update."""
import re

from ..config.constants import CATEGORIA_PADRAO, CATEGORIAS_VALIDAS, NOME_PRODUTO_MAX, NOME_PRODUTO_MIN
from ..middlewares.error_handler import ValidationError

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def require_body(dados):
    if not isinstance(dados, dict) or not dados:
        raise ValidationError("Dados inválidos")
    return dados


def validate_produto(dados):
    dados = require_body(dados)
    for campo, rotulo in (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque")):
        if campo not in dados:
            raise ValidationError(f"{rotulo} é obrigatório")

    nome = dados["nome"]
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", CATEGORIA_PADRAO)
    descricao = dados.get("descricao", "")

    if not isinstance(nome, str):
        raise ValidationError("Nome deve ser texto")
    if not _is_number(preco):
        raise ValidationError("Preço deve ser numérico")
    if not _is_int(estoque):
        raise ValidationError("Estoque deve ser um número inteiro")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_PRODUTO_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_PRODUTO_MAX:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)))

    return {"nome": nome, "descricao": descricao or "", "preco": preco, "estoque": estoque, "categoria": categoria}


def parse_optional_float(value, campo):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValidationError(f"Parâmetro {campo} deve ser numérico") from exc


def validate_novo_usuario(dados):
    dados = require_body(dados)
    nome, email, senha = (dados.get(k, "") for k in ("nome", "email", "senha"))
    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not isinstance(email, str) or not EMAIL_REGEX.match(email):
        raise ValidationError("Email inválido")
    return {"nome": nome, "email": email, "senha": senha}


def validate_login(dados):
    dados = dados if isinstance(dados, dict) else {}
    email, senha = dados.get("email", ""), dados.get("senha", "")
    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")
    return email, senha


def validate_pedido(dados):
    dados = require_body(dados)
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not _is_int(usuario_id):
        raise ValidationError("Usuario ID deve ser um número inteiro")
    if not isinstance(itens, list) or len(itens) == 0:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    validos = []
    for item in itens:
        if not isinstance(item, dict) or not _is_int(item.get("produto_id")) or not _is_int(item.get("quantidade")) \
                or item["quantidade"] <= 0:
            raise ValidationError("Cada item deve ter produto_id e quantidade inteira maior que zero")
        validos.append({"produto_id": item["produto_id"], "quantidade": item["quantidade"]})
    return usuario_id, validos


def validate_status(dados):
    dados = dados if isinstance(dados, dict) else {}
    return dados.get("status", "")
