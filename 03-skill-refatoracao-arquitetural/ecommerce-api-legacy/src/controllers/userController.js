'use strict';
const { ValidationError } = require('../utils/errors');

function makeUserController({ userService }) {
  return {
    async delete(req, res) {
      const userId = Number(req.params.id);
      if (!Number.isInteger(userId) || userId <= 0) throw new ValidationError('id inválido');
      await userService.deleteUser(userId);
      res.json({ msg: 'Usuário deletado (matrículas e pagamentos associados removidos)' });
    },
  };
}

module.exports = { makeUserController };
