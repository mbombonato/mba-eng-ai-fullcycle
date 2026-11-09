from flask import jsonify, request

from controllers.validators import validate_category
from views.serializers import category_view


class CategoryController:
    def __init__(self, category_service):
        self._categories = category_service

    def list(self):
        return jsonify([
            {**category_view(category), 'task_count': task_count}
            for category, task_count in self._categories.list_with_task_count()
        ]), 200

    def create(self):
        category = self._categories.create(validate_category(request.get_json(silent=True)))
        return jsonify(category_view(category)), 201

    def update(self, cat_id):
        self._categories.get(cat_id)
        category = self._categories.update(cat_id, validate_category(request.get_json(silent=True), partial=True))
        return jsonify(category_view(category)), 200

    def delete(self, cat_id):
        self._categories.delete(cat_id)
        return jsonify({'message': 'Categoria deletada'}), 200
