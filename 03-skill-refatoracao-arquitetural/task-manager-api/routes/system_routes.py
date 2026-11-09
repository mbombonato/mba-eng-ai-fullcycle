from flask import Blueprint


def create_system_blueprint(controller):
    bp = Blueprint('system', __name__)
    bp.add_url_rule('/', 'index', controller.index, methods=['GET'])
    bp.add_url_rule('/health', 'health', controller.health, methods=['GET'])
    return bp
