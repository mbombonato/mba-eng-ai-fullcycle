"""Entry point e application factory (composition root)."""
import logging

from flask import Flask
from flask_cors import CORS

from config.settings import Settings
from controllers.category_controller import CategoryController
from controllers.report_controller import ReportController
from controllers.system_controller import SystemController
from controllers.task_controller import TaskController
from controllers.user_controller import UserController
from database import db
from middlewares.error_handler import register_error_handlers
from routes.category_routes import create_category_blueprint
from routes.report_routes import create_report_blueprint
from routes.system_routes import create_system_blueprint
from routes.task_routes import create_task_blueprint
from routes.user_routes import create_user_blueprint
from services.auth_service import AuthService
from services.category_service import CategoryService
from services.report_service import ReportService
from services.task_service import TaskService
from services.user_service import UserService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings=None):
    settings = settings or Settings.from_env()

    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=settings.database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=settings.secret_key,
        DEBUG=settings.debug,
    )
    CORS(app, origins=settings.cors_origins)
    db.init_app(app)

    task_service = TaskService()
    user_service = UserService()
    category_service = CategoryService()
    auth_service = AuthService(settings.secret_key, settings.token_max_age_seconds)
    report_service = ReportService()

    app.register_blueprint(create_system_blueprint(SystemController()))
    app.register_blueprint(create_task_blueprint(TaskController(task_service)))
    app.register_blueprint(create_user_blueprint(UserController(user_service, task_service, auth_service)))
    app.register_blueprint(create_category_blueprint(CategoryController(category_service)))
    app.register_blueprint(create_report_blueprint(ReportController(report_service, user_service, task_service)))
    register_error_handlers(app)

    with app.app_context():
        import models  # noqa: F401 — registra os models antes do create_all
        db.create_all()

    app.extensions['settings'] = settings
    return app


app = create_app()

if __name__ == '__main__':
    current = app.extensions['settings']
    app.run(host=current.host, port=current.port, debug=current.debug)
