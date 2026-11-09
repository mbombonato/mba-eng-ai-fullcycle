"""Composition root: monta configuração, banco, models, services, controllers e rotas."""
from types import SimpleNamespace

from flask import Flask
from flask_cors import CORS

from .config.settings import Settings
from .controllers.pedido_controller import PedidoController
from .controllers.produto_controller import ProdutoController
from .controllers.sistema_controller import SistemaController
from .controllers.usuario_controller import UsuarioController
from .database import connection
from .database.schema import init_db
from .middlewares.error_handler import register_error_handlers
from .models.pedido_model import PedidoModel
from .models.produto_model import ProdutoModel
from .models.usuario_model import UsuarioModel
from .services.notificacao_service import NotificacaoService
from .services.pedido_service import PedidoService
from .services.relatorio_service import RelatorioService
from .views.routes import register_routes


def create_app(settings=None):
    settings = settings or Settings.from_env()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.secret_key,
        DEBUG=settings.debug,
        DATABASE_PATH=settings.database_path,
        ADMIN_TOKEN=settings.admin_token,
    )
    CORS(app, origins=settings.cors_origins)

    connection.init_app(app)
    init_db(settings.database_path)

    conn = connection.get_connection
    produto_model = ProdutoModel(conn)
    usuario_model = UsuarioModel(conn)
    pedido_model = PedidoModel(conn)

    pedido_service = PedidoService(pedido_model, produto_model, usuario_model, NotificacaoService())
    relatorio_service = RelatorioService(pedido_model)

    controllers = SimpleNamespace(
        produtos=ProdutoController(produto_model),
        usuarios=UsuarioController(usuario_model),
        pedidos=PedidoController(pedido_service),
        sistema=SistemaController(settings, conn, produto_model, usuario_model, pedido_model, relatorio_service),
    )

    register_routes(app, controllers)
    register_error_handlers(app)
    return app
