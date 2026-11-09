"""Tarefas assíncronas em memória (Asynchronous Request-Reply da F3).

Cada tarefa roda numa thread própria e passa por pending -> running -> done | failed.
O estado vive no processo da aplicação: reiniciar a aplicação perde as tarefas em
andamento, o que o desafio deixa fora de escopo (ADR 0004).
"""

import threading
import uuid
from collections.abc import Callable

from .errors import HelpdeskError
from .schemas import ReportStatus, TopicsReport

ProgressCallback = Callable[[int, int], None]


class _Job:
    def __init__(self):
        self.state = "pending"
        self.progress = None
        self.reason = None
        self.result: TopicsReport | None = None


class ReportJobs:
    def __init__(self):
        self._jobs: dict[str, _Job] = {}
        self._lock = threading.Lock()

    def submit(self, work: Callable[[ProgressCallback], TopicsReport]) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = _Job()
        with self._lock:
            self._jobs[job_id] = job
        threading.Thread(target=self._run, args=(job, work), name=f"report-{job_id}", daemon=True).start()
        return job_id

    def _run(self, job: _Job, work: Callable[[ProgressCallback], TopicsReport]) -> None:
        job.state = "running"

        def progress(done: int, total: int) -> None:
            job.progress = f"{done}/{total}"

        try:
            job.result = work(progress)
            job.state = "done"
        except HelpdeskError as error:
            job.reason, job.state = str(error), "failed"
        except Exception as error:  # nunca deixa a tarefa presa em running
            job.reason, job.state = f"Erro inesperado: {type(error).__name__}", "failed"

    def status(self, job_id: str) -> ReportStatus | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return ReportStatus(state=job.state, progress=job.progress, reason=job.reason)

    def result(self, job_id: str) -> TopicsReport | None:
        job = self._jobs.get(job_id)
        return job.result if job is not None else None
