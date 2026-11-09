'use strict';

// Express 4 não encaminha rejeições de handlers async ao middleware de erro.
const asyncHandler = (handler) => (req, res, next) => Promise.resolve(handler(req, res, next)).catch(next);

module.exports = { asyncHandler };
