'use strict';
const sqlite3 = require('sqlite3');

/**
 * Wrapper promisificado sobre o driver sqlite3 (substitui o callback hell).
 * `transaction(fn)` serializa as unidades de trabalho na conexão única e faz
 * COMMIT/ROLLBACK automaticamente.
 */
function createDatabase(filename) {
  const raw = new sqlite3.Database(filename);
  let queue = Promise.resolve();

  const run = (sql, params = []) =>
    new Promise((resolve, reject) => {
      raw.run(sql, params, function onRun(err) {
        if (err) return reject(err);
        return resolve({ lastID: this.lastID, changes: this.changes });
      });
    });

  const get = (sql, params = []) =>
    new Promise((resolve, reject) => raw.get(sql, params, (err, row) => (err ? reject(err) : resolve(row))));

  const all = (sql, params = []) =>
    new Promise((resolve, reject) => raw.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows))));

  const exec = (sql) => new Promise((resolve, reject) => raw.exec(sql, (err) => (err ? reject(err) : resolve())));

  const transaction = (work) => {
    const result = queue.then(async () => {
      await run('BEGIN IMMEDIATE');
      try {
        const value = await work();
        await run('COMMIT');
        return value;
      } catch (err) {
        await run('ROLLBACK');
        throw err;
      }
    });
    queue = result.catch(() => undefined); // mantém a fila viva após falhas
    return result;
  };

  const close = () => new Promise((resolve, reject) => raw.close((err) => (err ? reject(err) : resolve())));

  return { run, get, all, exec, transaction, close };
}

module.exports = { createDatabase };
