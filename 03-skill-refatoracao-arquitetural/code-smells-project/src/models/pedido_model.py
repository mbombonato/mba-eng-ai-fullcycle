"""Acesso a dados de pedidos e itens (sem N+1, escrita transacional)."""
from collections import defaultdict

from ..config.constants import STATUS_PEDIDO_APROVADO, STATUS_PEDIDO_CANCELADO, STATUS_PEDIDO_PENDENTE

PEDIDO_COLUMNS = "id, usuario_id, status, total, criado_em"


class EstoqueConcorrenteError(Exception):
    """Estoque mudou entre a validação e a baixa (corrida entre pedidos)."""


class PedidoModel:
    def __init__(self, connection_provider):
        self._conn = connection_provider

    def create_with_items(self, usuario_id, total, itens):
        """Cria pedido, itens e baixa estoque numa única transação.

        `itens` é uma lista de dicts com produto_id, quantidade e preco_unitario.
        """
        conn = self._conn()
        with conn:  # commit no sucesso, rollback em qualquer exceção
            pedido_id = conn.execute(
                "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
                (usuario_id, STATUS_PEDIDO_PENDENTE, total),
            ).lastrowid
            conn.executemany(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                [(pedido_id, i["produto_id"], i["quantidade"], i["preco_unitario"]) for i in itens],
            )
            for item in itens:
                baixa = conn.execute(
                    "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                    (item["quantidade"], item["produto_id"], item["quantidade"]),
                )
                if baixa.rowcount != 1:
                    raise EstoqueConcorrenteError(item["produto_id"])
        return pedido_id

    def list_all(self):
        return self._with_items(self._conn().execute(f"SELECT {PEDIDO_COLUMNS} FROM pedidos").fetchall())

    def list_by_usuario(self, usuario_id):
        rows = self._conn().execute(
            f"SELECT {PEDIDO_COLUMNS} FROM pedidos WHERE usuario_id = ?", (usuario_id,)
        ).fetchall()
        return self._with_items(rows)

    def _with_items(self, pedidos):
        """Carrega os itens de todos os pedidos em uma única query (JOIN com produtos)."""
        if not pedidos:
            return []
        ids = [p["id"] for p in pedidos]
        placeholders = ", ".join("?" for _ in ids)
        itens = self._conn().execute(
            f"""SELECT i.pedido_id, i.produto_id, i.quantidade, i.preco_unitario, p.nome AS produto_nome
                FROM itens_pedido i LEFT JOIN produtos p ON p.id = i.produto_id
                WHERE i.pedido_id IN ({placeholders}) ORDER BY i.id""",
            ids,
        ).fetchall()
        itens_por_pedido = defaultdict(list)
        for item in itens:
            itens_por_pedido[item["pedido_id"]].append(item)
        return [(pedido, itens_por_pedido[pedido["id"]]) for pedido in pedidos]

    def exists(self, pedido_id):
        return self._conn().execute("SELECT 1 FROM pedidos WHERE id = ?", (pedido_id,)).fetchone() is not None

    def update_status(self, pedido_id, status):
        conn = self._conn()
        with conn:
            conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))

    def sales_totals(self):
        """Agregações do relatório de vendas em uma única consulta."""
        return self._conn().execute(
            """SELECT COUNT(*) AS total_pedidos,
                      COALESCE(SUM(total), 0) AS faturamento,
                      COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS pendentes,
                      COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS aprovados,
                      COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS cancelados
               FROM pedidos""",
            (STATUS_PEDIDO_PENDENTE, STATUS_PEDIDO_APROVADO, STATUS_PEDIDO_CANCELADO),
        ).fetchone()

    def count(self):
        return self._conn().execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
