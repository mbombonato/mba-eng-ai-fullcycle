'use strict';
const crypto = require('node:crypto');
const { ForbiddenError } = require('../utils/errors');

/** Exige X-Admin-Token == ADMIN_TOKEN. Sem token configurado, as rotas admin ficam desabilitadas. */
function makeRequireAdmin(config) {
  const expected = Buffer.from(config.adminToken || '');
  return (req, res, next) => {
    const given = Buffer.from(req.get('X-Admin-Token') || '');
    const authorized = expected.length > 0 && given.length === expected.length && crypto.timingSafeEqual(given, expected);
    return authorized ? next() : next(new ForbiddenError());
  };
}

module.exports = { makeRequireAdmin };
