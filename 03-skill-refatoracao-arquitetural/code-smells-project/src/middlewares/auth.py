"""Autorização de rotas administrativas por token (X-Admin-Token)."""
import hmac
from functools import wraps

from flask import current_app, request

from .error_handler import ForbiddenError


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN", "")
        given = request.headers.get("X-Admin-Token", "")
        # Sem ADMIN_TOKEN configurado, as rotas administrativas ficam desabilitadas (fail-closed).
        if not expected or not hmac.compare_digest(given.encode(), expected.encode()):
            raise ForbiddenError("Acesso restrito a administradores")
        return view(*args, **kwargs)

    return wrapper
