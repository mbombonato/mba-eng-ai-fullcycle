'use strict';
const { PAYMENT_STATUS } = require('../config/constants');
const { NotFoundError, PaymentDeniedError, ValidationError } = require('../utils/errors');
const { hashPassword } = require('./passwordHasher');

function makeCheckoutService({ db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentGateway }) {
  return {
    /** Matricula o aluno no curso após pagamento aprovado. Todas as escritas são atômicas. */
    async checkout({ name, email, password, courseId, cardNumber }) {
      const course = await courseModel.findActiveById(courseId);
      if (!course) throw new NotFoundError('Curso não encontrado');

      const existingUser = await userModel.findByEmail(email);
      if (!existingUser && !password) throw new ValidationError('Senha é obrigatória para novos usuários');

      const status = paymentGateway.charge({ cardNumber, amount: course.price });
      if (status !== PAYMENT_STATUS.PAID) throw new PaymentDeniedError();

      return db.transaction(async () => {
        const userId = existingUser
          ? existingUser.id
          : await userModel.create({ name, email, passwordHash: hashPassword(password) });
        const enrollmentId = await enrollmentModel.create(userId, course.id);
        await paymentModel.create(enrollmentId, course.price, status);
        await auditLogModel.record(`Checkout curso ${course.id} por ${userId}`);
        return { enrollmentId };
      });
    },
  };
}

module.exports = { makeCheckoutService };
