"""Roteamento HTTP: método + caminho → controller (mesmas rotas da versão original)."""
from ..middlewares.auth import require_admin


def register_routes(app, c):
    """`c` é o container de controllers montado no composition root."""
    route = app.add_url_rule

    route("/", "index", c.sistema.index, methods=["GET"])
    route("/health", "health_check", c.sistema.health, methods=["GET"])

    route("/produtos", "listar_produtos", c.produtos.listar, methods=["GET"])
    route("/produtos/busca", "buscar_produtos", c.produtos.pesquisar, methods=["GET"])
    route("/produtos/<int:id>", "buscar_produto", c.produtos.buscar, methods=["GET"])
    route("/produtos", "criar_produto", c.produtos.criar, methods=["POST"])
    route("/produtos/<int:id>", "atualizar_produto", c.produtos.atualizar, methods=["PUT"])
    route("/produtos/<int:id>", "deletar_produto", c.produtos.deletar, methods=["DELETE"])

    route("/usuarios", "listar_usuarios", c.usuarios.listar, methods=["GET"])
    route("/usuarios/<int:id>", "buscar_usuario", c.usuarios.buscar, methods=["GET"])
    route("/usuarios", "criar_usuario", c.usuarios.criar, methods=["POST"])
    route("/login", "login", c.usuarios.login, methods=["POST"])

    route("/pedidos", "criar_pedido", c.pedidos.criar, methods=["POST"])
    route("/pedidos", "listar_todos_pedidos", c.pedidos.listar_todos, methods=["GET"])
    route("/pedidos/usuario/<int:usuario_id>", "listar_pedidos_usuario", c.pedidos.listar_por_usuario, methods=["GET"])
    route("/pedidos/<int:pedido_id>/status", "atualizar_status_pedido", c.pedidos.atualizar_status, methods=["PUT"])

    route("/relatorios/vendas", "relatorio_vendas", c.sistema.relatorio_vendas, methods=["GET"])

    # Administração: protegida por X-Admin-Token. O antigo POST /admin/query (SQL arbitrário) foi removido.
    route("/admin/reset-db", "reset_database", require_admin(c.sistema.reset_database), methods=["POST"])
