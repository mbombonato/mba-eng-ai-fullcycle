"""Exceções de domínio e tratamento centralizado de erros."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 400

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


def _error(message, status):
    return jsonify({"erro": message, "sucesso": False}), status


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return _error(err.message, err.status_code)

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return _error(err.description, err.code)

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Erro inesperado: %s", err)
        return _error("Erro interno do servidor", 500)
