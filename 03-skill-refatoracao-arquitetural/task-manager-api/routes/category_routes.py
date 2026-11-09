from flask import Blueprint


def create_category_blueprint(controller):
    bp = Blueprint('categories', __name__)
    bp.add_url_rule('/categories', 'get_categories', controller.list, methods=['GET'])
    bp.add_url_rule('/categories', 'create_category', controller.create, methods=['POST'])
    bp.add_url_rule('/categories/<int:cat_id>', 'update_category', controller.update, methods=['PUT'])
    bp.add_url_rule('/categories/<int:cat_id>', 'delete_category', controller.delete, methods=['DELETE'])
    return bp
