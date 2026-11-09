"""Casos de uso de tasks."""
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from config.constants import CLOSED_TASK_STATUSES, TASK_STATUS_DONE, TASK_STATUSES
from database import db
from middlewares.error_handler import NotFoundError
from models.category import Category
from models.task import Task
from models.user import User
from utils.clock import utcnow


def overdue_filter(now):
    return db.and_(Task.due_date.is_not(None), Task.due_date < now, Task.status.not_in(CLOSED_TASK_STATUSES))


class TaskService:
    def get(self, task_id):
        task = db.session.get(Task, task_id)
        if task is None:
            raise NotFoundError('Task não encontrada')
        return task

    def list_with_relations(self):
        stmt = db.select(Task).options(selectinload(Task.user), selectinload(Task.category)).order_by(Task.id)
        return db.session.scalars(stmt).all()

    def list_by_user(self, user_id):
        return db.session.scalars(db.select(Task).filter_by(user_id=user_id).order_by(Task.id)).all()

    def search(self, query=None, status=None, priority=None, user_id=None):
        stmt = db.select(Task)
        if query:
            stmt = stmt.where(db.or_(Task.title.like(f'%{query}%'), Task.description.like(f'%{query}%')))
        if status:
            stmt = stmt.where(Task.status == status)
        if priority is not None:
            stmt = stmt.where(Task.priority == priority)
        if user_id is not None:
            stmt = stmt.where(Task.user_id == user_id)
        return db.session.scalars(stmt.order_by(Task.id)).all()

    def _ensure_references(self, fields):
        if fields.get('user_id') and db.session.get(User, fields['user_id']) is None:
            raise NotFoundError('Usuário não encontrado')
        if fields.get('category_id') and db.session.get(Category, fields['category_id']) is None:
            raise NotFoundError('Categoria não encontrada')

    def create(self, fields):
        self._ensure_references(fields)
        task = Task(**fields)
        db.session.add(task)
        db.session.commit()
        return task

    def update(self, task_id, fields):
        task = self.get(task_id)
        self._ensure_references(fields)
        for key, value in fields.items():
            setattr(task, key, value)
        task.updated_at = utcnow()
        db.session.commit()
        return task

    def delete(self, task_id):
        db.session.delete(self.get(task_id))
        db.session.commit()

    def stats(self):
        counts = dict(db.session.execute(db.select(Task.status, func.count()).group_by(Task.status)).all())
        total = sum(counts.values())
        done = counts.get(TASK_STATUS_DONE, 0)
        overdue = db.session.scalar(db.select(func.count()).select_from(Task).where(overdue_filter(utcnow())))
        stats = {'total': total}
        stats.update({status: counts.get(status, 0) for status in TASK_STATUSES})
        stats['overdue'] = overdue
        stats['completion_rate'] = round((done / total) * 100, 2) if total > 0 else 0
        return stats
