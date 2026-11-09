'use strict';
// Único módulo que lê variáveis de ambiente. `.env` é opcional (Node >= 20.12 / 21.7).
try {
  process.loadEnvFile();
} catch {
  /* sem .env: usa apenas o ambiente do processo */
}

module.exports = Object.freeze({
  port: Number(process.env.PORT || 3000),
  databaseFile: process.env.DATABASE_FILE || ':memory:',
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
  adminToken: process.env.ADMIN_TOKEN || '',
});
