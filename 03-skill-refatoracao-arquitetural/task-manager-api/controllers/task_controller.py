import logging

from flask import jsonify, request

from controllers.validators import parse_int_arg, validate_task
from utils.clock import utcnow
from views.serializers import task_view

logger = logging.getLogger(__name__)


class TaskController:
    def __init__(self, task_service):
        self._tasks = task_service

    def list(self):
        now = utcnow()
        tasks = self._tasks.list_with_relations()
        return jsonify([task_view(t, overdue=t.is_overdue(now), with_relations=True) for t in tasks]), 200

    def get(self, task_id):
        task = self._tasks.get(task_id)
        return jsonify(task_view(task, overdue=task.is_overdue())), 200

    def create(self):
        task = self._tasks.create(validate_task(request.get_json(silent=True)))
        logger.info("Task criada id=%s", task.id)
        return jsonify(task_view(task)), 201

    def update(self, task_id):
        self._tasks.get(task_id)  # 404 antes de validar o corpo, como na versão original
        task = self._tasks.update(task_id, validate_task(request.get_json(silent=True), partial=True))
        logger.info("Task atualizada id=%s", task.id)
        return jsonify(task_view(task)), 200

    def delete(self, task_id):
        self._tasks.delete(task_id)
        logger.info("Task deletada id=%s", task_id)
        return jsonify({'message': 'Task deletada com sucesso'}), 200

    def search(self):
        tasks = self._tasks.search(
            query=request.args.get('q', ''),
            status=request.args.get('status', ''),
            priority=parse_int_arg(request.args.get('priority'), 'priority'),
            user_id=parse_int_arg(request.args.get('user_id'), 'user_id'),
        )
        return jsonify([task_view(t) for t in tasks]), 200

    def stats(self):
        return jsonify(self._tasks.stats()), 200
