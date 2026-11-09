from datetime import datetime


class SystemController:
    def index(self):
        return {'message': 'Task Manager API', 'version': '1.0'}

    def health(self):
        return {'status': 'ok', 'timestamp': str(datetime.now())}
