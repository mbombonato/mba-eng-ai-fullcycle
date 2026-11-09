from flask import Blueprint


def create_report_blueprint(controller):
    bp = Blueprint('reports', __name__)
    bp.add_url_rule('/reports/summary', 'summary_report', controller.summary, methods=['GET'])
    bp.add_url_rule('/reports/user/<int:user_id>', 'user_report', controller.user_report, methods=['GET'])
    return bp
