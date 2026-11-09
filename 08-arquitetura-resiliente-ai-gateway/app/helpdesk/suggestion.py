from .ports import TextModel
from .schemas import ReplySuggestion, TicketInput

CAPABILITY = "reply-suggestion"


def suggest(ticket: TicketInput, model: TextModel) -> ReplySuggestion:
    text = model.complete(CAPABILITY, "suggest", ticket.text)
    return ReplySuggestion(ticket_id=ticket.ticket_id, suggestion=text)
