'use strict';
const { PAYMENT_STATUS, APPROVED_CARD_PREFIX } = require('../config/constants');

/** Gateway de pagamento simulado. Nunca registra o número completo do cartão nem a chave. */
function makePaymentGateway({ config, logger }) {
  if (!config.paymentGatewayKey) logger.warn('PAYMENT_GATEWAY_KEY não configurada (gateway em modo simulado)');
  return {
    charge({ cardNumber, amount }) {
      logger.info(`Processando pagamento de ${amount} no cartão final ${cardNumber.slice(-4)}`);
      return cardNumber.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
    },
  };
}

module.exports = { makePaymentGateway };
