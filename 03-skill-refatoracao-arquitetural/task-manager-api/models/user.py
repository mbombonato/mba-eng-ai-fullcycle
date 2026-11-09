import hashlib
import hmac
import re

from werkzeug.security import check_password_hash, generate_password_hash

from config.constants import DEFAULT_ROLE
from database import db
from utils.clock import utcnow

_LEGACY_MD5 = re.compile(r"^[0-9a-f]{32}$")


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=DEFAULT_ROLE)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)  # scrypt com salt

    def check_password(self, raw_password):
        """Verifica a senha; hashes MD5 legados são migrados para scrypt no primeiro login válido."""
        if self.password and _LEGACY_MD5.match(self.password):
            legacy = hashlib.md5(raw_password.encode()).hexdigest()  # noqa: S324 — só para migração
            if not hmac.compare_digest(self.password, legacy):
                return False
            self.set_password(raw_password)
            return True
        return check_password_hash(self.password, raw_password)
