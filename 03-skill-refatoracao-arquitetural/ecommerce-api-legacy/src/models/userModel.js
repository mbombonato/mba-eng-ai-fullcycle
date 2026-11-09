'use strict';

function makeUserModel(db) {
  return {
    findById: (id) => db.get('SELECT id, name, email FROM users WHERE id = ?', [id]),
    findByEmail: (email) => db.get('SELECT id, name, email FROM users WHERE email = ?', [email]),
    async create({ name, email, passwordHash }) {
      const { lastID } = await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [name, email, passwordHash]);
      return lastID;
    },
    delete: (id) => db.run('DELETE FROM users WHERE id = ?', [id]),
  };
}

module.exports = { makeUserModel };
