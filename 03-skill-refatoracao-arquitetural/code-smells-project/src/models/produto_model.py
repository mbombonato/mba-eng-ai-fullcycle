"""Acesso a dados de produtos (somente queries parametrizadas)."""

PRODUTO_COLUMNS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


class ProdutoModel:
    def __init__(self, connection_provider):
        self._conn = connection_provider

    def list_all(self):
        return self._conn().execute(f"SELECT {PRODUTO_COLUMNS} FROM produtos").fetchall()

    def find_by_id(self, produto_id):
        return self._conn().execute(
            f"SELECT {PRODUTO_COLUMNS} FROM produtos WHERE id = ?", (produto_id,)
        ).fetchone()

    def find_by_ids(self, produto_ids):
        ids = list(set(produto_ids))
        if not ids:
            return {}
        placeholders = ", ".join("?" for _ in ids)
        rows = self._conn().execute(
            f"SELECT {PRODUTO_COLUMNS} FROM produtos WHERE id IN ({placeholders})", ids
        ).fetchall()
        return {row["id"]: row for row in rows}

    def search(self, termo=None, categoria=None, preco_min=None, preco_max=None):
        clauses, params = [], []
        if termo:
            clauses.append("(nome LIKE ? OR descricao LIKE ?)")
            params += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            clauses.append("categoria = ?")
            params.append(categoria)
        if preco_min is not None:
            clauses.append("preco >= ?")
            params.append(preco_min)
        if preco_max is not None:
            clauses.append("preco <= ?")
            params.append(preco_max)
        where = " AND ".join(clauses) if clauses else "1=1"
        return self._conn().execute(f"SELECT {PRODUTO_COLUMNS} FROM produtos WHERE {where}", params).fetchall()

    def create(self, nome, descricao, preco, estoque, categoria):
        conn = self._conn()
        with conn:
            cursor = conn.execute(
                "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
                (nome, descricao, preco, estoque, categoria),
            )
        return cursor.lastrowid

    def update(self, produto_id, nome, descricao, preco, estoque, categoria):
        conn = self._conn()
        with conn:
            conn.execute(
                "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
                (nome, descricao, preco, estoque, categoria, produto_id),
            )

    def delete(self, produto_id):
        conn = self._conn()
        with conn:
            conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))

    def count(self):
        return self._conn().execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
