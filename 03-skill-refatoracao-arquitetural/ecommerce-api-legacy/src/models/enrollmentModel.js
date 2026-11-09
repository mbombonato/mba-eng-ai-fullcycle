'use strict';

function makeEnrollmentModel(db) {
  return {
    async create(userId, courseId) {
      const { lastID } = await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [userId, courseId]);
      return lastID;
    },
    deleteByUser: (userId) => db.run('DELETE FROM enrollments WHERE user_id = ?', [userId]),
    /** Cursos com matrículas, alunos e pagamentos em uma única consulta (sem N+1). */
    financialRows: () =>
      db.all(`
        SELECT c.id AS course_id, c.title AS course_title,
               e.id AS enrollment_id, u.name AS student_name,
               p.amount AS payment_amount, p.status AS payment_status
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id = c.id
        LEFT JOIN users u ON u.id = e.user_id
        LEFT JOIN payments p ON p.enrollment_id = e.id
        ORDER BY c.id, e.id`),
  };
}

module.exports = { makeEnrollmentModel };
