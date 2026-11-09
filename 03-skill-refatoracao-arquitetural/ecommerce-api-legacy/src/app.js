'use strict';
const express = require('express');
const { makeUserModel } = require('./models/userModel');
const { makeCourseModel } = require('./models/courseModel');
const { makeEnrollmentModel } = require('./models/enrollmentModel');
const { makePaymentModel } = require('./models/paymentModel');
const { makeAuditLogModel } = require('./models/auditLogModel');
const { makePaymentGateway } = require('./services/paymentGateway');
const { makeCheckoutService } = require('./services/checkoutService');
const { makeReportService } = require('./services/reportService');
const { makeUserService } = require('./services/userService');
const { makeCheckoutController } = require('./controllers/checkoutController');
const { makeReportController } = require('./controllers/reportController');
const { makeUserController } = require('./controllers/userController');
const { makeRequireAdmin } = require('./middlewares/requireAdmin');
const { makeErrorHandler } = require('./middlewares/errorHandler');
const { makeRouter } = require('./views/routes');

/** Composition root: cria e injeta todas as dependências. */
function createApp({ db, config, logger }) {
  const models = {
    userModel: makeUserModel(db),
    courseModel: makeCourseModel(db),
    enrollmentModel: makeEnrollmentModel(db),
    paymentModel: makePaymentModel(db),
    auditLogModel: makeAuditLogModel(db),
  };
  const paymentGateway = makePaymentGateway({ config, logger });
  const services = {
    checkout: makeCheckoutService({ db, ...models, paymentGateway }),
    report: makeReportService(models),
    user: makeUserService({ db, ...models }),
  };
  const controllers = {
    checkout: makeCheckoutController({ checkoutService: services.checkout }),
    report: makeReportController({ reportService: services.report }),
    user: makeUserController({ userService: services.user }),
  };

  const app = express();
  app.use(express.json());
  app.use('/api', makeRouter({ controllers, requireAdmin: makeRequireAdmin(config) }));
  app.use(makeErrorHandler(logger));
  return app;
}

module.exports = { createApp };
