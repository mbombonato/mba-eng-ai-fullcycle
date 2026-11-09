'use strict';

function makeAuditLogModel(db) {
  return {
    record: (action) => db.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [action]),
  };
}

module.exports = { makeAuditLogModel };
