"""Casos de uso de usuários."""
from sqlalchemy import func

from database import db
from middlewares.error_handler import ConflictError, NotFoundError
from models.task import Task
from models.user import User


class UserService:
    def get(self, user_id):
        user = db.session.get(User, user_id)
        if user is None:
            raise NotFoundError('Usuário não encontrado')
        return user

    def list_with_task_count(self):
        users = db.session.scalars(db.select(User).order_by(User.id)).all()
        counts = dict(db.session.execute(
            db.select(Task.user_id, func.count()).where(Task.user_id.is_not(None)).group_by(Task.user_id)
        ).all())
        return [(user, counts.get(user.id, 0)) for user in users]

    def _ensure_email_available(self, email, current_user_id=None):
        existing = db.session.scalar(db.select(User).filter_by(email=email))
        if existing is not None and existing.id != current_user_id:
            raise ConflictError('Email já cadastrado')

    def create(self, fields):
        self._ensure_email_available(fields['email'])
        user = User(name=fields['name'], email=fields['email'], role=fields['role'])
        user.set_password(fields['password'])
        db.session.add(user)
        db.session.commit()
        return user

    def update(self, user_id, fields):
        user = self.get(user_id)
        if 'email' in fields:
            self._ensure_email_available(fields['email'], current_user_id=user_id)
        for key, value in fields.items():
            if key == 'password':
                user.set_password(value)
            else:
                setattr(user, key, value)
        db.session.commit()
        return user

    def delete(self, user_id):
        user = self.get(user_id)
        db.session.execute(db.delete(Task).where(Task.user_id == user_id))  # tasks do usuário (1 query)
        db.session.delete(user)
        db.session.commit()
