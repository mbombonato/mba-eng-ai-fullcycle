'use strict';
const { ValidationError } = require('../utils/errors');
const { CARD_NUMBER_PATTERN, EMAIL_PATTERN } = require('../config/constants');

/** Mapeia o contrato público (usr, eml, pwd, c_id, card) para nomes de domínio e valida. */
function parseCheckoutInput(body = {}) {
  const { usr: name, eml: email, pwd: password, c_id: rawCourseId, card } = body;
  if (!name || !email || !rawCourseId || !card) throw new ValidationError('Bad Request');

  const courseId = Number(rawCourseId);
  const cardNumber = String(card).replace(/\s+/g, '');
  if (!Number.isInteger(courseId) || courseId <= 0) throw new ValidationError('c_id inválido');
  if (!EMAIL_PATTERN.test(String(email))) throw new ValidationError('Email inválido');
  if (!CARD_NUMBER_PATTERN.test(cardNumber)) throw new ValidationError('Cartão inválido');
  if (password !== undefined && typeof password !== 'string') throw new ValidationError('Senha inválida');

  return { name: String(name), email: String(email), password, courseId, cardNumber };
}

function makeCheckoutController({ checkoutService }) {
  return {
    async checkout(req, res) {
      const { enrollmentId } = await checkoutService.checkout(parseCheckoutInput(req.body));
      res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
    },
  };
}

module.exports = { makeCheckoutController };
