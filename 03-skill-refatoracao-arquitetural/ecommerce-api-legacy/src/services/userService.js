'use strict';
const { NotFoundError } = require('../utils/errors');

function makeUserService({ db, userModel, enrollmentModel, paymentModel }) {
  return {
    /** Remove o usuário com suas matrículas e pagamentos (sem deixar registros órfãos). */
    async deleteUser(userId) {
      const user = await userModel.findById(userId);
      if (!user) throw new NotFoundError('Usuário não encontrado');
      await db.transaction(async () => {
        await paymentModel.deleteByUser(userId);
        await enrollmentModel.deleteByUser(userId);
        await userModel.delete(userId);
      });
    },
  };
}

module.exports = { makeUserService };
