'use strict';
const { PAYMENT_STATUS } = require('../config/constants');

function makeReportService({ enrollmentModel }) {
  return {
    /** Receita (somente pagamentos PAID) e alunos por curso. */
    async financialReport() {
      const rows = await enrollmentModel.financialRows();
      const byCourse = new Map();
      for (const row of rows) {
        if (!byCourse.has(row.course_id)) {
          byCourse.set(row.course_id, { course: row.course_title, revenue: 0, students: [] });
        }
        if (row.enrollment_id === null) continue; // curso sem matrículas
        const entry = byCourse.get(row.course_id);
        if (row.payment_status === PAYMENT_STATUS.PAID) entry.revenue += row.payment_amount;
        entry.students.push({
          student: row.student_name ?? 'Unknown',
          paid: row.payment_amount ?? 0,
        });
      }
      return [...byCourse.values()];
    },
  };
}

module.exports = { makeReportService };
