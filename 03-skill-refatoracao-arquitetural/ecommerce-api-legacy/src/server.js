'use strict';
const config = require('./config');
const logger = require('./utils/logger');
const { createDatabase } = require('./database/connection');
const { initSchema } = require('./database/schema');
const { createApp } = require('./app');

async function main() {
  const db = createDatabase(config.databaseFile);
  await initSchema(db);
  const app = createApp({ db, config, logger });
  const server = app.listen(config.port, () => logger.info(`LMS API rodando na porta ${config.port}`));
  server.on('error', (err) => {
    logger.error(`Não foi possível escutar na porta ${config.port}:`, err.message);
    process.exit(1);
  });
}

main().catch((err) => {
  logger.error('Falha ao iniciar a aplicação:', err);
  process.exit(1);
});
