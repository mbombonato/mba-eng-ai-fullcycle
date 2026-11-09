'use strict';
const express = require('express');
const { asyncHandler } = require('../middlewares/asyncHandler');

/** Rotas públicas da API (mesmos métodos e caminhos da versão legada). */
function makeRouter({ controllers, requireAdmin }) {
  const router = express.Router();
  router.post('/checkout', asyncHandler(controllers.checkout.checkout));
  router.get('/admin/financial-report', requireAdmin, asyncHandler(controllers.report.financialReport));
  router.delete('/users/:id', requireAdmin, asyncHandler(controllers.user.delete));
  return router;
}

module.exports = { makeRouter };
