import logging

from flask import jsonify, request

from controllers.validators import validate_login, validate_new_user, validate_user_update
from utils.clock import utcnow
from views.serializers import task_summary_view, task_view, user_view

logger = logging.getLogger(__name__)


class UserController:
    def __init__(self, user_service, task_service, auth_service):
        self._users = user_service
        self._tasks = task_service
        self._auth = auth_service

    def list(self):
        return jsonify([
            {**user_view(user), 'task_count': task_count}
            for user, task_count in self._users.list_with_task_count()
        ]), 200

    def get(self, user_id):
        data = user_view(self._users.get(user_id))
        data['tasks'] = [task_view(t) for t in self._tasks.list_by_user(user_id)]
        return jsonify(data), 200

    def create(self):
        user = self._users.create(validate_new_user(request.get_json(silent=True)))
        logger.info("Usuário criado id=%s", user.id)
        return jsonify(user_view(user)), 201

    def update(self, user_id):
        self._users.get(user_id)
        user = self._users.update(user_id, validate_user_update(request.get_json(silent=True)))
        return jsonify(user_view(user)), 200

    def delete(self, user_id):
        self._users.delete(user_id)
        logger.info("Usuário deletado id=%s", user_id)
        return jsonify({'message': 'Usuário deletado com sucesso'}), 200

    def tasks(self, user_id):
        self._users.get(user_id)
        now = utcnow()
        return jsonify([task_summary_view(t, t.is_overdue(now)) for t in self._tasks.list_by_user(user_id)]), 200

    def login(self):
        email, password = validate_login(request.get_json(silent=True))
        user, token = self._auth.login(email, password)
        return jsonify({'message': 'Login realizado com sucesso', 'user': user_view(user), 'token': token}), 200
