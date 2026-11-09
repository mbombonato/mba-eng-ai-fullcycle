'use strict';

class AppError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.name = this.constructor.name;
    this.status = status;
  }
}

class ValidationError extends AppError {
  constructor(message) { super(message, 400); }
}

class PaymentDeniedError extends AppError {
  constructor(message = 'Pagamento recusado') { super(message, 400); }
}

class ForbiddenError extends AppError {
  constructor(message = 'Acesso restrito a administradores') { super(message, 403); }
}

class NotFoundError extends AppError {
  constructor(message) { super(message, 404); }
}

module.exports = { AppError, ValidationError, PaymentDeniedError, ForbiddenError, NotFoundError };
