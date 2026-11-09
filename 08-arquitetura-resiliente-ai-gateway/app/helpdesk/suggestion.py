from collections.abc import Iterator

from .ports import TextModel
from .schemas import TicketInput

CAPABILITY = "reply-suggestion"


def suggest(ticket: TicketInput, model: TextModel) -> Iterator[str]:
    """Trechos da sugestão de resposta, na ordem em que o modelo os gera."""
    return model.stream(CAPABILITY, "suggest", ticket.text)
