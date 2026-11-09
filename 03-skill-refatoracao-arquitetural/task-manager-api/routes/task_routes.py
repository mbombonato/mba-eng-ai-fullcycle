from flask import Blueprint


def create_task_blueprint(controller):
    bp = Blueprint('tasks', __name__)
    bp.add_url_rule('/tasks', 'get_tasks', controller.list, methods=['GET'])
    bp.add_url_rule('/tasks/<int:task_id>', 'get_task', controller.get, methods=['GET'])
    bp.add_url_rule('/tasks', 'create_task', controller.create, methods=['POST'])
    bp.add_url_rule('/tasks/<int:task_id>', 'update_task', controller.update, methods=['PUT'])
    bp.add_url_rule('/tasks/<int:task_id>', 'delete_task', controller.delete, methods=['DELETE'])
    bp.add_url_rule('/tasks/search', 'search_tasks', controller.search, methods=['GET'])
    bp.add_url_rule('/tasks/stats', 'task_stats', controller.stats, methods=['GET'])
    return bp
