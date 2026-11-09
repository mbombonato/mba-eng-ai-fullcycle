'use strict';

function makePaymentModel(db) {
  return {
    create: (enrollmentId, amount, status) =>
      db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [enrollmentId, amount, status]),
    deleteByUser: (userId) =>
      db.run('DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)', [userId]),
  };
}

module.exports = { makePaymentModel };
