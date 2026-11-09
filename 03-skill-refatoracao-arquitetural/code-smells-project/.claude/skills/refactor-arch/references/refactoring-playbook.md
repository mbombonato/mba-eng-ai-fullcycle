# Playbook de Refatoração (Fase 3)

Transformações concretas por anti-pattern. Os exemplos mostram Python (Flask) e JavaScript
(Express); em outras stacks, aplique o mesmo princípio com a API idiomática equivalente.
Aplique em ordem de severidade e valide com o smoke test ao final de cada bloco grande.

---

## P-01 — Configuração por variáveis de ambiente (AP-01, AP-10)

**Antes**
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.run(host="0.0.0.0", port=5000, debug=True)
```
```js
const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_123", port: 3000 };
```

**Depois**
```python
# config/settings.py
import os, secrets

class Settings:
    def __init__(self, env=os.environ):
        self.SECRET_KEY = env.get("SECRET_KEY") or secrets.token_hex(32)  # efêmera em dev
        self.DEBUG = env.get("FLASK_DEBUG", "0") == "1"                    # default seguro
        self.HOST = env.get("HOST", "127.0.0.1")
        self.PORT = int(env.get("PORT", "5000"))
        self.DATABASE_PATH = env.get("DATABASE_PATH", "loja.db")
```
```js
// src/config/index.js
try { process.loadEnvFile(); } catch { /* .env opcional */ }
module.exports = Object.freeze({
  port: Number(process.env.PORT || 3000),
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
  adminToken: process.env.ADMIN_TOKEN || '',
});
```
+ `.env.example` com as chaves (sem valores reais). Remova chaves que não são usadas por nenhum código.

---

## P-02 — Queries parametrizadas (AP-02)

**Antes**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
query += " AND (nome LIKE '%" + termo + "%')"
```
**Depois**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))   # senha verificada por hash (P-04)

clauses, params = ["1=1"], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
cursor.execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params)  # só placeholders interpolados
```
```js
db.get('SELECT * FROM users WHERE email = ?', [email]);
```
Regra: **nenhum** valor vindo do usuário entra na string SQL; só nomes de coluna fixos do código.

---

## P-03 — Decompor God Class / God File em camadas (AP-03, AP-20, AP-22)

**Antes** (`AppManager.js`: banco + schema + rotas + pagamento em uma classe)
```js
class AppManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE ... INSERT seed */ }
  setupRoutes(app) {
    app.post('/api/checkout', (req, res) => { /* validação + SQL + pagamento + auditoria */ });
  }
}
```
**Depois**
```
src/
├── config/index.js
├── database/connection.js       # abre a conexão, schema e seed
├── models/{user,course,enrollment,payment,auditLog}Model.js
├── services/{paymentGateway,checkoutService,reportService}.js
├── controllers/{checkout,report,user}Controller.js
├── views/routes.js              # app.post('/api/checkout', checkoutController.checkout)
├── middlewares/{errorHandler,requireAdmin}.js
└── app.js                       # createApp(): injeta tudo
```
```js
// controllers/checkoutController.js — só fluxo
const makeCheckoutController = ({ checkoutService }) => ({
  async checkout(req, res) {
    const input = parseCheckoutInput(req.body);           // valida (P-16)
    const result = await checkoutService.checkout(input); // regra no service
    res.status(200).json({ msg: 'Sucesso', enrollment_id: result.enrollmentId });
  },
});
```
Passos: (1) listar responsabilidades do arquivo; (2) criar um módulo por responsabilidade/
agregado; (3) mover código sem mudar comportamento; (4) ligar no composition root; (5) apagar o arquivo antigo.

---

## P-04 — Hash de senha seguro + migração de legados (AP-05)

**Antes**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
```
```js
function badCrypto(pwd) { let h = ""; for (let i = 0; i < 10000; i++) h += Buffer.from(pwd).toString('base64').substring(0, 2); return h.substring(0, 10); }
let hash = badCrypto(p || "123456");
```
**Depois**
```python
from werkzeug.security import generate_password_hash, check_password_hash  # já vem com Flask

def set_password(self, raw):
    self.password = generate_password_hash(raw)        # scrypt/pbkdf2 com salt

def check_password(self, raw):
    if _is_legacy_md5(self.password):                  # migração transparente
        ok = hmac.compare_digest(self.password, hashlib.md5(raw.encode()).hexdigest())
        if ok:
            self.set_password(raw)                     # rehash no primeiro login
        return ok
    return check_password_hash(self.password, raw)
```
```js
const crypto = require('node:crypto');
function hashPassword(raw) {
  const salt = crypto.randomBytes(16).toString('hex');
  return `scrypt$${salt}$${crypto.scryptSync(raw, salt, 64).toString('hex')}`;
}
// senha obrigatória: sem default "123456" — ausência vira ValidationError (400)
```

---

## P-05 — Error handling centralizado (AP-16)

**Antes**
```python
def listar_produtos():
    try:
        ...
    except Exception as e:
        return jsonify({"erro": str(e)}), 500     # repetido em todo handler, vaza detalhes
```
**Depois**
```python
# middlewares/error_handler.py
class AppError(Exception):
    status = 400
    def __init__(self, message): super().__init__(message); self.message = message
class NotFoundError(AppError): status = 404
class ValidationError(AppError): status = 400

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def _app_error(err): return jsonify({"erro": err.message, "sucesso": False}), err.status
    @app.errorhandler(Exception)
    def _unexpected(err):
        app.logger.exception("Erro inesperado")
        return jsonify({"erro": "Erro interno do servidor", "sucesso": False}), 500

# controller fica sem try/except:
def buscar_produto(id):
    return jsonify({"dados": produto_view(service.get(id)), "sucesso": True}), 200
```
```js
// middlewares/errorHandler.js (Express: 4 argumentos, registrado por último)
module.exports = (err, req, res, next) => {
  const status = err.status || 500;
  if (status >= 500) logger.error(err);
  res.status(status).json({ error: status >= 500 ? 'Erro interno' : err.message });
};
// Express 4 não captura rejeições de async: envolva handlers
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
```
Nunca use `except:` nu — capture a exceção específica.

---

## P-06 — Eliminar N+1 (AP-13)

**Antes**
```python
for row in pedidos:
    cursor.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in cursor.fetchall():
        cursor.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
**Depois** (1 query com JOIN, agrupamento em memória)
```python
rows = conn.execute("""
    SELECT i.pedido_id, i.produto_id, i.quantidade, i.preco_unitario, p.nome AS produto_nome
    FROM itens_pedido i LEFT JOIN produtos p ON p.id = i.produto_id
    WHERE i.pedido_id IN (SELECT id FROM pedidos WHERE usuario_id = ?)""", (usuario_id,)).fetchall()
itens_por_pedido = defaultdict(list)
for r in rows: itens_por_pedido[r["pedido_id"]].append(r)
```
ORM (SQLAlchemy): `db.select(Task).options(selectinload(Task.user), selectinload(Task.category))`;
contagens: `db.select(Task.status, func.count()).group_by(Task.status)` em vez de 1 `COUNT` por status.

---

## P-07 — Extrair regra de negócio do controller para service/model (AP-07, AP-15)

**Antes**
```python
@task_bp.route('/tasks')
def get_tasks():
    for t in Task.query.all():
        if t.due_date:
            if t.due_date < datetime.utcnow():
                if t.status != 'done' and t.status != 'cancelled':
                    task_data['overdue'] = True   # mesma lógica copiada em 5 rotas
```
**Depois**
```python
# models/task.py — regra intrínseca da entidade, em um só lugar
def is_overdue(self, now=None):
    now = now or utcnow()
    return bool(self.due_date and self.due_date < now and self.status not in CLOSED_STATUSES)

# controllers/task_controller.py — só fluxo
def list_tasks():
    return jsonify([task_view(t, with_relations=True) for t in task_service.list_all()]), 200
```
Notificações/side effects (`print("ENVIANDO EMAIL")`) vão para um `NotificationService` chamado pelo service do caso de uso.

---

## P-08 — Remover estado global e injetar dependências (AP-08, AP-09)

**Antes**
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect("loja.db", check_same_thread=False)
    return db_connection
```
```js
let globalCache = {};
class AppManager { constructor() { this.db = new sqlite3.Database(':memory:'); } }
```
**Depois**
```python
# database/connection.py — conexão por request, guardada no contexto do Flask
def get_connection():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db

def init_app(app):
    app.teardown_appcontext(lambda exc: g.pop("db", None) and None or _close(exc))
```
```js
// app.js — composition root
function createApp({ db, config }) {
  const userModel = makeUserModel(db);
  const checkoutService = makeCheckoutService({ db, userModel, paymentGateway: makePaymentGateway(config) });
  ...
}
```
Cache, se necessário, vira um objeto com dono (instância injetada, com limite), nunca variável de módulo.

---

## P-09 — Transações para escritas multi-etapas e cascata (AP-12, AP-19)

**Antes**
```python
for item in itens:
    ... if produto["estoque"] < item["quantidade"]: return {"erro": ...}  # após inserts parciais?
cursor.execute("INSERT INTO pedidos ...")
for item in itens: cursor.execute("INSERT INTO itens_pedido ..."); cursor.execute("UPDATE produtos ...")
db.commit()
```
**Depois**
```python
with conn:                       # sqlite3: commit no sucesso, rollback em exceção
    pedido_id = conn.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)", (...)).lastrowid
    conn.executemany("INSERT INTO itens_pedido (...) VALUES (?, ?, ?, ?)", linhas)
    conn.executemany("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", baixas)
```
```js
await db.transaction(async (tx) => {
  const enrollmentId = await tx.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [userId, courseId]);
  await tx.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [enrollmentId, price, 'PAID']);
});
// exclusão em cascata: apagar filhos (payments → enrollments) e o pai na MESMA transação
```

---

## P-10 — Callbacks → async/await (AP-18)

**Antes**
```js
this.db.all("SELECT * FROM courses", [], (err, courses) => {
  courses.forEach(c => {
    this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {
      enrollments.forEach(enr => { this.db.get(..., (err, user) => { this.db.get(..., (err, payment) => {
        pending--; if (pending === 0) res.json(report);
      }); }); });
    });
  });
});
```
**Depois**
```js
// database/connection.js — wrapper promisificado
const all = (sql, params = []) => new Promise((resolve, reject) =>
  db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows))));

// services/reportService.js
async function financialReport() {
  const rows = await db.all(`SELECT c.id, c.title, u.name, p.amount, p.status
                             FROM courses c
                             LEFT JOIN enrollments e ON e.course_id = c.id
                             LEFT JOIN users u ON u.id = e.user_id
                             LEFT JOIN payments p ON p.enrollment_id = e.id
                             ORDER BY c.id, e.id`);
  return groupByCourse(rows);   // 1 query, ordem determinística
}
```

---

## P-11 — Não expor dados sensíveis (AP-06)

**Antes**
```python
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password, ...}
return jsonify({..., "secret_key": "minha-chave-super-secreta-123", "db_path": "loja.db"})
```
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
**Depois**
```python
PUBLIC_USER_FIELDS = ("id", "name", "email", "role", "active", "created_at")
def user_view(user):                       # whitelist na view
    return {f: getattr(user, f) for f in PUBLIC_USER_FIELDS}
# health: apenas status e contagens
```
```js
logger.info(`Processando pagamento do cartão final ${card.slice(-4)}`);  // nunca PAN completo nem chave
```

---

## P-12 — Substituir APIs deprecated (AP-17)

**Antes**
```python
from datetime import datetime
task = Task.query.get(task_id)
created_at = db.Column(db.DateTime, default=datetime.utcnow)
```
**Depois**
```python
from datetime import datetime, timezone
def utcnow():                               # naive UTC, compatível com colunas existentes
    return datetime.now(timezone.utc).replace(tzinfo=None)
task = db.session.get(Task, task_id)
created_at = db.Column(db.DateTime, default=utcnow)
```
```js
const buf = Buffer.from(str);           // em vez de new Buffer(str)
const url = new URL(req.url, base);     // em vez de url.parse
res.sendStatus(204);                    // em vez de res.send(204)
```

---

## P-13 — Magic numbers/strings → constantes nomeadas (AP-21, AP-15)

**Antes**
```python
if faturamento > 10000: desconto = faturamento * 0.1
elif faturamento > 5000: desconto = faturamento * 0.05
if novo_status not in ["pendente", "aprovado", "enviado", "entregue", "cancelado"]: ...
```
**Depois**
```python
# config/constants.py
ORDER_STATUSES = ("pendente", "aprovado", "enviado", "entregue", "cancelado")
DISCOUNT_TIERS = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))   # (faturamento mínimo, taxa)

def discount_for(revenue):
    return next((revenue * rate for threshold, rate in DISCOUNT_TIERS if revenue > threshold), 0)
```

---

## P-14 — Proteger/remover endpoints perigosos e tokens falsos (AP-04, AP-11)

**Antes**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json()["sql"])          # SQL arbitrário, sem auth
return {"token": "fake-jwt-token-" + str(user.id)}
```
**Depois**
```python
# endpoint de SQL arbitrário: REMOVIDO (não existe forma segura de expô-lo)

# middlewares/auth.py
def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config["ADMIN_TOKEN"]
        given = request.headers.get("X-Admin-Token", "")
        if not expected or not hmac.compare_digest(given, expected):
            raise ForbiddenError("Acesso restrito a administradores")
        return view(*args, **kwargs)
    return wrapper

# token assinado e com expiração
from itsdangerous import URLSafeTimedSerializer
token = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth").dumps({"user_id": user.id})
```
```js
function requireAdmin(config) {
  return (req, res, next) => {
    const given = Buffer.from(req.get('X-Admin-Token') || '');
    const expected = Buffer.from(config.adminToken || '');
    if (!expected.length || given.length !== expected.length || !crypto.timingSafeEqual(given, expected))
      return next(new ForbiddenError('Acesso restrito a administradores'));
    next();
  };
}
```

---

## P-15 — Logging estruturado em vez de print (AP-23)

**Antes**
```python
print("Produto criado com ID: " + str(id))
print("ERRO: " + str(e))
```
**Depois**
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Produto criado id=%s", produto_id)
logger.exception("Falha ao criar produto")   # dentro do error handler, com stacktrace
```
```js
const logger = { info: (...a) => console.info('[INFO]', ...a), error: (...a) => console.error('[ERROR]', ...a) };
```

---

## P-16 — Camada de validação única por recurso (AP-14, AP-15)

**Antes**
```python
if priority < 1 or priority > 5:    # TypeError 500 se priority == "alta"
...
if len(data['title']) < 3: ...      # regra repetida, diferente em create e update
```
**Depois**
```python
# controllers/validators.py
def parse_priority(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("Prioridade deve ser um inteiro entre 1 e 5")
    if not MIN_PRIORITY <= value <= MAX_PRIORITY:
        raise ValidationError("Prioridade deve ser entre 1 e 5")
    return value

def validate_task_payload(data, partial=False):
    """Mesmas regras para create (partial=False) e update (partial=True)."""
```
```js
function parseCheckoutInput(body = {}) {
  const { usr, eml, pwd, c_id: courseId, card } = body;
  if (!usr || !eml || !courseId || !card) throw new ValidationError('Bad Request');
  return { name: usr, email: eml, password: pwd, courseId: Number(courseId), card: String(card) };
}
```

---

## Índice

| Playbook | Resolve |
|---|---|
| P-01 Config por ambiente | AP-01, AP-10 |
| P-02 Queries parametrizadas | AP-02 |
| P-03 Decompor God Class | AP-03, AP-20, AP-22 |
| P-04 Hash de senha | AP-05 |
| P-05 Error handler central | AP-16 |
| P-06 Eliminar N+1 | AP-13 |
| P-07 Regra → service/model | AP-07, AP-15 |
| P-08 DI / sem estado global | AP-08, AP-09 |
| P-09 Transações e cascata | AP-12, AP-19 |
| P-10 Callbacks → async/await | AP-18 |
| P-11 Não expor dados sensíveis | AP-06 |
| P-12 APIs deprecated | AP-17 |
| P-13 Constantes nomeadas | AP-21, AP-15 |
| P-14 Endpoints admin / tokens | AP-04, AP-11 |
| P-15 Logging | AP-23 |
| P-16 Validação | AP-14 |
