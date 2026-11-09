"""Notificações (simuladas via log; ponto único para plugar e-mail/SMS/push reais)."""
import logging

from ..config.constants import STATUS_PEDIDO_APROVADO, STATUS_PEDIDO_CANCELADO

logger = logging.getLogger(__name__)


class NotificacaoService:
    def pedido_criado(self, pedido_id, usuario_id):
        logger.info("Notificação [email/sms/push]: pedido %s criado para usuário %s", pedido_id, usuario_id)

    def status_alterado(self, pedido_id, status):
        if status == STATUS_PEDIDO_APROVADO:
            logger.info("Notificação: pedido %s aprovado, preparar envio", pedido_id)
        elif status == STATUS_PEDIDO_CANCELADO:
            logger.info("Notificação: pedido %s cancelado", pedido_id)
