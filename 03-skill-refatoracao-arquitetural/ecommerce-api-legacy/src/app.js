const express = require('express');
const AppManager = require('./AppManager');
const { config } = require('./utils');

const app = express();
app.use(express.json());

const manager = new AppManager();
manager.initDb();
manager.setupRoutes(app);

app.listen(config.port, () => {
    console.log(`Frankenstein LMS rodando na porta ${config.port}...`);
});
