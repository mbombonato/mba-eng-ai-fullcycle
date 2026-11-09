"""Erros do domínio do helpdesk. A camada HTTP (main) decide o status de cada um."""


class HelpdeskError(Exception):
    """Base dos erros que a aplicação sabe explicar ao cliente."""


class InvalidInput(HelpdeskError):
    """A entrada é sintaticamente válida, mas não faz sentido (ex.: período invertido)."""


class InvalidModelOutput(HelpdeskError):
    """O modelo respondeu algo fora do contrato da feature."""


class ModelUnavailable(HelpdeskError):
    """Nenhum destino da capacidade respondeu: primário, fallbacks e tempo esgotados."""


class QuotaExceeded(HelpdeskError):
    """O gateway recusou a chamada por orçamento ou limite de requisições."""


class GenerationInterrupted(HelpdeskError):
    """Um stream começou e foi interrompido antes do fim."""
