'use strict';
const { AppError } = require('../utils/errors');

function makeErrorHandler(logger) {
  // eslint-disable-next-line no-unused-vars -- Express identifica error handlers pela aridade 4
  return (err, req, res, next) => {
    if (err instanceof AppError) return res.status(err.status).json({ error: err.message });
    if (err.type === 'entity.parse.failed') return res.status(400).json({ error: 'JSON inválido' });
    logger.error(`Erro inesperado em ${req.method} ${req.originalUrl}:`, err);
    return res.status(500).json({ error: 'Erro interno do servidor' });
  };
}

module.exports = { makeErrorHandler };
