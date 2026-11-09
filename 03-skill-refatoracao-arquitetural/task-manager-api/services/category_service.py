"""Casos de uso de categorias."""
from sqlalchemy import func

from database import db
from middlewares.error_handler import NotFoundError
from models.category import Category
from models.task import Task


class CategoryService:
    def get(self, category_id):
        category = db.session.get(Category, category_id)
        if category is None:
            raise NotFoundError('Categoria não encontrada')
        return category

    def list_with_task_count(self):
        categories = db.session.scalars(db.select(Category).order_by(Category.id)).all()
        counts = dict(db.session.execute(
            db.select(Task.category_id, func.count()).where(Task.category_id.is_not(None)).group_by(Task.category_id)
        ).all())
        return [(category, counts.get(category.id, 0)) for category in categories]

    def create(self, fields):
        category = Category(**fields)
        db.session.add(category)
        db.session.commit()
        return category

    def update(self, category_id, fields):
        category = self.get(category_id)
        for key, value in fields.items():
            setattr(category, key, value)
        db.session.commit()
        return category

    def delete(self, category_id):
        category = self.get(category_id)
        # desassocia as tasks na mesma transação para não deixar category_id órfão
        db.session.execute(db.update(Task).where(Task.category_id == category_id).values(category_id=None))
        db.session.delete(category)
        db.session.commit()
