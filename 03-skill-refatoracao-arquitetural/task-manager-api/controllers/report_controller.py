from flask import jsonify


class ReportController:
    def __init__(self, report_service, user_service, task_service):
        self._reports = report_service
        self._users = user_service
        self._tasks = task_service

    def summary(self):
        return jsonify(self._reports.summary()), 200

    def user_report(self, user_id):
        user = self._users.get(user_id)
        return jsonify(self._reports.user_report(user, self._tasks.list_by_user(user_id))), 200
