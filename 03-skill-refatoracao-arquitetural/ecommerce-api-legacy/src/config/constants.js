'use strict';

const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

// Gateway simulado: cartões iniciados com este prefixo são aprovados (regra do sistema legado).
const APPROVED_CARD_PREFIX = '4';
const CARD_NUMBER_PATTERN = /^\d{12,19}$/;
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

module.exports = { PAYMENT_STATUS, APPROVED_CARD_PREFIX, CARD_NUMBER_PATTERN, EMAIL_PATTERN };
