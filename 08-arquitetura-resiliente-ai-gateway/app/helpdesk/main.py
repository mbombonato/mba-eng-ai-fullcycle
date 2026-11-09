"""Ponto de composição: monta os adaptadores concretos e expõe as rotas HTTP.

Modos de execução (ADR 0004):
- F1 e F4: síncronos, com timeout explícito;
- F2: streaming (Server-Sent Events);
- F3: assíncrono (Asynchronous Request-Reply: 202 + Location + Retry-After).
"""

import json
from collections.abc import Iterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

from . import classification, config, extraction, report, suggestion
from .adapters.gateway import GatewayTextModel
from .errors import (HelpdeskError, InvalidInput, InvalidModelOutput, ModelUnavailable,
                     QuotaExceeded)
from .jobs import ReportJobs
from .schemas import Classification, OrderData, PeriodInput, ReportStatus, TicketInput, TopicsReport
from .tickets import JsonlTicketSource

app = FastAPI(title="Helpdesk")

realtime_model = GatewayTextModel(config.GATEWAY_URL, config.GATEWAY_REALTIME_KEY,
                                  config.MAX_OUTPUT_TOKENS, config.REALTIME_TIMEOUT_SECONDS)
reports_model = GatewayTextModel(config.GATEWAY_URL, config.GATEWAY_REPORTS_KEY,
                                 config.MAX_OUTPUT_TOKENS, config.REPORT_CALL_TIMEOUT_SECONDS)
ticket_source = JsonlTicketSource(config.TICKETS_FILE)
report_jobs = ReportJobs()

ERROR_STATUS = {InvalidInput: 422, InvalidModelOutput: 502, QuotaExceeded: 429, ModelUnavailable: 503}


@app.exception_handler(HelpdeskError)
def helpdesk_error(request: Request, error: HelpdeskError) -> JSONResponse:
    return JSONResponse({"detail": str(error)}, status_code=ERROR_STATUS.get(type(error), 503))


@app.get("/health")
def health():
    return {"status": "ok"}


# F1: síncrono.
@app.post("/tickets/classification")
def classify_ticket(ticket: TicketInput) -> Classification:
    return classification.classify(ticket, realtime_model)


# F2: streaming (SSE).
def _sse(data: dict, event: str | None = None) -> str:
    head = f"event: {event}\n" if event else ""
    return f"{head}data: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/tickets/reply-suggestion")
def suggest_reply(ticket: TicketInput):
    chunks = suggestion.suggest(ticket, realtime_model)
    # Espera o primeiro trecho antes de responder: se nenhum modelo atender, o cliente
    # recebe um erro HTTP explícito (503/429) em vez de um stream vazio.
    first = next(chunks, None)

    def events() -> Iterator[str]:
        try:
            if first is not None:
                yield _sse({"chunk": first})
            for chunk in chunks:
                yield _sse({"chunk": chunk})
        except HelpdeskError:
            yield _sse({"ticket_id": ticket.ticket_id, "message": "A geração foi interrompida"}, "error")
            return
        yield _sse({"ticket_id": ticket.ticket_id}, "end")

    # X-Accel-Buffering: no desliga o buffer do nginx da borda só para esta resposta.
    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(events(), media_type="text/event-stream", headers=headers)


# F3: assíncrono (Asynchronous Request-Reply).
@app.post("/reports/topics", status_code=202)
def request_topics_report(period: PeriodInput) -> JSONResponse:
    report.validate(period)
    job_id = report_jobs.submit(lambda progress: report.topics(
        period, reports_model, ticket_source, config.TICKETS_PER_CALL,
        config.REPORT_CONCURRENCY, config.REPORT_DEADLINE_SECONDS, progress))
    status_url = f"/reports/topics/status/{job_id}"
    return JSONResponse({"id": job_id, "state": "pending", "status_url": status_url}, status_code=202,
                        headers={"Location": status_url, "Retry-After": str(config.REPORT_RETRY_AFTER_SECONDS)})


@app.get("/reports/topics/status/{job_id}", response_model=None)
def topics_report_status(job_id: str) -> ReportStatus | JSONResponse | RedirectResponse:
    status = report_jobs.status(job_id)
    if status is None:
        return JSONResponse({"detail": "Relatório não encontrado"}, status_code=404)
    if status.state == "done":
        return RedirectResponse(f"/reports/topics/{job_id}", status_code=303)
    headers = {} if status.state == "failed" else {"Retry-After": str(config.REPORT_RETRY_AFTER_SECONDS)}
    return JSONResponse(status.model_dump(exclude_none=True), headers=headers)


@app.get("/reports/topics/{job_id}", response_model=None)
def topics_report_result(job_id: str) -> TopicsReport | JSONResponse:
    result = report_jobs.result(job_id)
    if result is None:
        return JSONResponse({"detail": "Relatório não encontrado ou ainda não concluído"}, status_code=404)
    return result


# F4: síncrono.
@app.post("/tickets/extraction")
def extract_order_data(ticket: TicketInput) -> OrderData:
    return extraction.extract(ticket, realtime_model)
