'use strict';
const crypto = require('node:crypto');

const KEY_LENGTH = 64;

/** Hash adaptativo com salt aleatório (scrypt da stdlib), substitui o antigo `badCrypto`. */
function hashPassword(rawPassword) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(rawPassword, salt, KEY_LENGTH).toString('hex');
  return `scrypt$${salt}$${hash}`;
}

module.exports = { hashPassword };
