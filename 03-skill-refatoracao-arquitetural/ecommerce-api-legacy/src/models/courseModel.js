'use strict';

function makeCourseModel(db) {
  return {
    findActiveById: (id) => db.get('SELECT id, title, price FROM courses WHERE id = ? AND active = 1', [id]),
  };
}

module.exports = { makeCourseModel };
