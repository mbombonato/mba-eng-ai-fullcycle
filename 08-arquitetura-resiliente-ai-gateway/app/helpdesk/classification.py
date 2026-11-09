import json

from .errors import InvalidModelOutput
from .ports import TextModel
from .schemas import Classification, TicketInput

CAPABILITY = "ticket-classification"
CATEGORIES = {"delivery", "payment", "exchange_return", "product_defect", "other"}
PRIORITIES = {"low", "medium", "high"}


def classify(ticket: TicketInput, model: TextModel) -> Classification:
    data = json.loads(model.complete(CAPABILITY, "classify", ticket.text))
    if data.get("category") not in CATEGORIES or data.get("priority") not in PRIORITIES:
        raise InvalidModelOutput("Classificação fora dos valores permitidos")
    return Classification(ticket_id=ticket.ticket_id, **data)
