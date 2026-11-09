"""Relatórios de produtividade (agregações no banco, sem N+1)."""
from datetime import timedelta

from sqlalchemy import case, func

from config.constants import (
    HIGH_PRIORITY_THRESHOLD, PRIORITY_LABELS, RECENT_ACTIVITY_DAYS, TASK_STATUS_DONE, TASK_STATUSES,
)
from database import db
from models.category import Category
from models.task import Task
from models.user import User
from services.task_service import overdue_filter
from utils.clock import utcnow


def _rate(part, total):
    return round((part / total) * 100, 2) if total > 0 else 0


def _count(model):
    return db.session.scalar(db.select(func.count()).select_from(model))


class ReportService:
    def summary(self):
        now = utcnow()
        since = now - timedelta(days=RECENT_ACTIVITY_DAYS)

        by_status = dict(db.session.execute(db.select(Task.status, func.count()).group_by(Task.status)).all())
        by_priority = dict(db.session.execute(db.select(Task.priority, func.count()).group_by(Task.priority)).all())
        overdue_tasks = db.session.scalars(db.select(Task).where(overdue_filter(now)).order_by(Task.id)).all()
        recent_created = db.session.scalar(
            db.select(func.count()).select_from(Task).where(Task.created_at >= since))
        recent_done = db.session.scalar(db.select(func.count()).select_from(Task).where(
            Task.status == TASK_STATUS_DONE, Task.updated_at >= since))

        done_expr = func.sum(case((Task.status == TASK_STATUS_DONE, 1), else_=0))
        per_user = {row.user_id: row for row in db.session.execute(
            db.select(Task.user_id, func.count().label('total'), done_expr.label('done'))
            .where(Task.user_id.is_not(None)).group_by(Task.user_id)
        )}
        users = db.session.scalars(db.select(User).order_by(User.id)).all()

        user_stats = []
        for user in users:
            row = per_user.get(user.id)
            total, completed = (row.total, row.done) if row else (0, 0)
            user_stats.append({
                'user_id': user.id,
                'user_name': user.name,
                'total_tasks': total,
                'completed_tasks': completed,
                'completion_rate': _rate(completed, total),
            })

        return {
            'generated_at': str(now),
            'overview': {
                'total_tasks': sum(by_status.values()),
                'total_users': _count(User),
                'total_categories': _count(Category),
            },
            'tasks_by_status': {status: by_status.get(status, 0) for status in TASK_STATUSES},
            'tasks_by_priority': {label: by_priority.get(p, 0) for p, label in PRIORITY_LABELS.items()},
            'overdue': {
                'count': len(overdue_tasks),
                'tasks': [{
                    'id': t.id,
                    'title': t.title,
                    'due_date': str(t.due_date),
                    'days_overdue': (now - t.due_date).days,
                } for t in overdue_tasks],
            },
            'recent_activity': {
                'tasks_created_last_7_days': recent_created,
                'tasks_completed_last_7_days': recent_done,
            },
            'user_productivity': user_stats,
        }

    def user_report(self, user, tasks):
        now = utcnow()
        counts = {status: 0 for status in TASK_STATUSES}
        for task in tasks:
            if task.status in counts:
                counts[task.status] += 1
        return {
            'user': {'id': user.id, 'name': user.name, 'email': user.email},
            'statistics': {
                'total_tasks': len(tasks),
                'done': counts['done'],
                'pending': counts['pending'],
                'in_progress': counts['in_progress'],
                'cancelled': counts['cancelled'],
                'overdue': sum(1 for t in tasks if t.is_overdue(now)),
                'high_priority': sum(1 for t in tasks if t.priority <= HIGH_PRIORITY_THRESHOLD),
                'completion_rate': _rate(counts['done'], len(tasks)),
            },
        }
