from flask import Blueprint


def create_user_blueprint(controller):
    bp = Blueprint('users', __name__)
    bp.add_url_rule('/users', 'get_users', controller.list, methods=['GET'])
    bp.add_url_rule('/users/<int:user_id>', 'get_user', controller.get, methods=['GET'])
    bp.add_url_rule('/users', 'create_user', controller.create, methods=['POST'])
    bp.add_url_rule('/users/<int:user_id>', 'update_user', controller.update, methods=['PUT'])
    bp.add_url_rule('/users/<int:user_id>', 'delete_user', controller.delete, methods=['DELETE'])
    bp.add_url_rule('/users/<int:user_id>/tasks', 'get_user_tasks', controller.tasks, methods=['GET'])
    bp.add_url_rule('/login', 'login', controller.login, methods=['POST'])
    return bp
