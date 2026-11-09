'use strict';

function makeReportController({ reportService }) {
  return {
    async financialReport(req, res) {
      res.json(await reportService.financialReport());
    },
  };
}

module.exports = { makeReportController };
