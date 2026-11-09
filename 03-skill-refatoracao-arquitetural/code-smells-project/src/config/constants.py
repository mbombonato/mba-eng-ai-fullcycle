"""Constantes de domínio (antes espalhadas como magic numbers/strings)."""

CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
CATEGORIA_PADRAO = "geral"

NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200

TIPO_USUARIO_PADRAO = "cliente"

STATUS_PEDIDO_PENDENTE = "pendente"
STATUS_PEDIDO_APROVADO = "aprovado"
STATUS_PEDIDO_CANCELADO = "cancelado"
STATUS_PEDIDO = (STATUS_PEDIDO_PENDENTE, STATUS_PEDIDO_APROVADO, "enviado", "entregue", STATUS_PEDIDO_CANCELADO)

# (faturamento mínimo exclusivo, taxa de desconto) — avaliados em ordem decrescente
FAIXAS_DESCONTO = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))
