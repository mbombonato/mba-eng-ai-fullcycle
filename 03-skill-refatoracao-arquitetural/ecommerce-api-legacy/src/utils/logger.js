'use strict';

const write = (level, stream) => (...args) => stream(`${new Date().toISOString()} [${level}]`, ...args);

module.exports = Object.freeze({
  info: write('INFO', console.info),
  warn: write('WARN', console.warn),
  error: write('ERROR', console.error),
});
