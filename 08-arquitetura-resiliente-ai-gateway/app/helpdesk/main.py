"""Ponto de composição: monta os adaptadores concretos e expõe as rotas HTTP.

As features recebem as portas (TextModel, TicketSource) prontas; só este módulo conhece
o adaptador do gateway e a configuração. Os modos de resposta são os da v1 (síncronos).
"""

from fastapi import FastAPI

from . import classification, config, extraction, report, suggestion
from .adapters.gateway import GatewayTextModel
from .schemas import (Classification, OrderData, PeriodInput, ReplySuggestion, TicketInput,
                      TopicsReport)
from .tickets import JsonlTicketSource

app = FastAPI(title="Helpdesk")

realtime_model = GatewayTextModel(config.GATEWAY_URL, config.GATEWAY_REALTIME_KEY,
                                  config.MAX_OUTPUT_TOKENS, config.GATEWAY_TIMEOUT_SECONDS)
reports_model = GatewayTextModel(config.GATEWAY_URL, config.GATEWAY_REPORTS_KEY,
                                 config.MAX_OUTPUT_TOKENS, config.GATEWAY_TIMEOUT_SECONDS)
ticket_source = JsonlTicketSource(config.TICKETS_FILE)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tickets/classification")
def classify_ticket(ticket: TicketInput) -> Classification:
    return classification.classify(ticket, realtime_model)


@app.post("/tickets/reply-suggestion")
def suggest_reply(ticket: TicketInput) -> ReplySuggestion:
    return suggestion.suggest(ticket, realtime_model)


@app.post("/tickets/extraction")
def extract_order_data(ticket: TicketInput) -> OrderData:
    return extraction.extract(ticket, realtime_model)


@app.post("/reports/topics")
def topics_report(period: PeriodInput) -> TopicsReport:
    return report.topics(period, reports_model, ticket_source, config.TICKETS_PER_CALL)
