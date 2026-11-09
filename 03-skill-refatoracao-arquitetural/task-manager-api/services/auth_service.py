"""Autenticação: verificação de credenciais e emissão de token assinado."""
from itsdangerous import URLSafeTimedSerializer

from database import db
from middlewares.error_handler import ForbiddenError, UnauthorizedError
from models.user import User

TOKEN_SALT = 'task-manager-auth'


class AuthService:
    def __init__(self, secret_key, max_age_seconds):
        self._serializer = URLSafeTimedSerializer(secret_key, salt=TOKEN_SALT)
        self._max_age = max_age_seconds

    def login(self, email, password):
        user = db.session.scalar(db.select(User).filter_by(email=email))
        if user is None or not user.check_password(password):
            raise UnauthorizedError('Credenciais inválidas')
        if not user.active:
            raise ForbiddenError('Usuário inativo')
        db.session.commit()  # persiste eventual migração de hash legado
        return user, self._serializer.dumps({'user_id': user.id})

    def verify_token(self, token):
        """Retorna o user_id do token válido e não expirado (para proteger rotas futuramente)."""
        return self._serializer.loads(token, max_age=self._max_age)['user_id']
