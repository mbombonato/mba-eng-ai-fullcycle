# Catálogo de Anti-patterns (Fase 2)

Escala de severidade (baseada em MVC/SOLID e segurança):

- **CRITICAL** — falha grave de segurança ou de arquitetura: expõe dados sensíveis, permite injeção,
  ou viola completamente a separação de responsabilidades (God Class).
- **HIGH** — forte violação de MVC/SOLID que dificulta muito manutenção e testes (regra de negócio
  em controller/rota, acoplamento sem DI, estado global mutável, configuração insegura).
- **MEDIUM** — padronização, duplicação, performance moderada (N+1), validação ausente,
  tratamento de erros inconsistente, APIs deprecated.
- **LOW** — legibilidade: nomes ruins, magic numbers, prints, imports mortos.

Cada entrada traz: **sinais de detecção** (o que procurar — grep e leitura), **por que importa** e a
**transformação** do playbook. Os greps são ponto de partida: sempre confirme lendo o trecho.

---

## CRITICAL

### AP-01 — Credenciais / segredos hardcoded
- **Sinais:** literais atribuídos a `SECRET_KEY`, `password`, `pass`, `senha`, `token`, `api_key`,
  `*_KEY`, `smtp`, `pk_live_`, `sk_live_`, connection strings com usuário:senha.
  ```bash
  grep -rnEi "(secret|passw|senha|pass|token|api_?key|key|user)\w*['\"]?\]?\s*[:=]\s*['\"][^'\"]+['\"]|(pk|sk)_live_" \
    --include='*.py' --include='*.js' --include='*.ts' . | grep -v -e node_modules -e .venv
  ```
  O padrão cobre `KEY = "x"`, `config["SECRET_KEY"] = "x"`, `self.email_password = 'x'` e
  `paymentGatewayKey: "x"` (camelCase). Também procure segredos em literais de resposta
  (`"secret_key": ...` dentro de `jsonify`) e usuários/senhas em seeds.
- **Por que importa:** segredo vai para o versionamento; vazamento compromete produção; impossível rotacionar por ambiente.
- **Fix:** Playbook **P-01** (config por variáveis de ambiente).

### AP-02 — SQL Injection (query por concatenação/interpolação)
- **Sinais:** `execute("..." + var)`, `execute(f"...{var}")`, `"... WHERE id = " + str(id)`,
  template string JS `` `SELECT ... ${x}` ``, `"%s" % var` dentro de SQL, `LIKE '%" + termo + "%'`.
  `grep -nE "execute\(.*(\+|f\"|%)|(SELECT|INSERT|UPDATE|DELETE).*\"\s*\+" -r .`
- **Por que importa:** permite bypass de login (`' --`), leitura/escrita arbitrária; também quebra com dados legítimos que contêm aspas.
- **Fix:** **P-02** (queries parametrizadas).

### AP-03 — God Class / God File
- **Sinais:** um arquivo/classe que contém roteamento **e** SQL **e** regra de negócio (ex.: classe
  `*Manager` com `setupRoutes` + `CREATE TABLE` + cálculo de pagamento); `models.py` com SQL,
  validação e formatação de vários domínios; arquivo > ~300 linhas com > 3 responsabilidades.
- **Por que importa:** viola SRP; impossível testar isoladamente; toda mudança afeta tudo.
- **Fix:** **P-03** (decomposição em camadas MVC).

### AP-04 — Endpoint administrativo perigoso / sem autenticação
- **Sinais:** rota que executa SQL/código recebido no corpo (`cursor.execute(request.json["sql"])`,
  `eval`, `exec`); rotas destrutivas (`reset`, `DELETE` em massa, `/admin/*`) sem verificação de
  identidade/permissão.
- **Por que importa:** qualquer cliente anônimo apaga ou exfiltra a base inteira.
- **Fix:** **P-14** (remover execução arbitrária; proteger rotas admin com middleware de autorização).

### AP-05 — Armazenamento inseguro de senhas
- **Sinais:** senha gravada em texto puro (`INSERT ... senha` com o valor recebido); `hashlib.md5`,
  `sha1`, hash sem salt; "criptografia" caseira (base64 em loop); senha **default** quando o
  cliente não envia (`pwd || "123456"`); comparação `senha = '<input>'` no SQL.
- **Por que importa:** vazamento do banco expõe senhas reais (reutilizadas em outros serviços); MD5 é quebrado por força bruta em segundos.
- **Fix:** **P-04** (hash adaptativo com salt: scrypt/pbkdf2/bcrypt + migração de hashes legados).

### AP-06 — Exposição de dados sensíveis
- **Sinais:** serialização que inclui `senha`/`password`/hash (`to_dict` com password, `SELECT *`
  devolvido inteiro); endpoint de health/debug devolvendo `secret_key`, `db_path`, `debug`;
  logs com número de cartão, chave de gateway, senha (`console.log(... card ...)`).
- **Por que importa:** vazamento direto de credenciais e dados de pagamento (PCI-DSS/LGPD).
- **Fix:** **P-11** (whitelist de campos na view/serializer; mascarar logs).

---

## HIGH

### AP-07 — Regra de negócio no controller/rota (Fat Controller)
- **Sinais:** handler HTTP com cálculos, regras de desconto/aprovação, orquestração de várias
  queries, montagem manual de dicionários campo a campo, notificações (`print("ENVIANDO EMAIL")`);
  handler com > ~40 linhas.
- **Por que importa:** regra fica presa ao framework web, não é reutilizável nem testável sem HTTP.
- **Fix:** **P-07** (extrair para service/model; controller só orquestra).

### AP-08 — Estado global mutável
- **Sinais:** variáveis de módulo reatribuídas/mutadas (`global db_connection`, `let globalCache = {}`,
  `let totalRevenue = 0`, listas em atributo de singleton que só crescem); conexão única
  compartilhada entre threads (`check_same_thread=False`).
- **Por que importa:** acoplamento oculto, condições de corrida, vazamento de memória, testes que interferem entre si.
- **Fix:** **P-08** (estado em instâncias injetadas / escopo de request).

### AP-09 — Acoplamento forte sem injeção de dependência
- **Sinais:** classe que instancia sua própria infraestrutura (`this.db = new sqlite3.Database(...)`
  no construtor, `NotificationService()` criado dentro do handler); módulos importando a conexão
  global diretamente em todas as camadas; impossível trocar o banco num teste.
- **Por que importa:** viola DIP; impede testes e troca de implementação.
- **Fix:** **P-08** (composition root cria e injeta dependências).

### AP-10 — Configuração insegura de execução
- **Sinais:** `debug=True` / `DEBUG = True` fixo no código, `app.run(host="0.0.0.0", debug=True)`,
  `CORS(app)` liberando qualquer origem sem configuração, porta/URIs fixas.
- **Por que importa:** o debugger do Werkzeug permite execução remota de código; configuração não varia por ambiente.
- **Fix:** **P-01** (flags vindas do ambiente, default seguro).

### AP-11 — Autenticação falsa / token previsível
- **Sinais:** `'fake-jwt-token-' + str(user.id)`, token = id/email, token sem assinatura nem expiração.
- **Por que importa:** qualquer um forja o token de qualquer usuário.
- **Fix:** **P-14** (token assinado com segredo e expiração — ex.: `itsdangerous`, JWT, `crypto.createHmac`).

### AP-12 — Escrita multi-etapas sem transação
- **Sinais:** vários `INSERT/UPDATE` encadeados (pedido + itens + estoque; matrícula + pagamento +
  auditoria) sem `BEGIN/COMMIT/ROLLBACK`; `return` de erro no meio do loop após escritas parciais;
  callbacks que ignoram `err` entre etapas.
- **Por que importa:** falha no meio deixa dados inconsistentes (pagamento sem matrícula, estoque baixado sem pedido).
- **Fix:** **P-09** (unidade de trabalho / transação).

---

## MEDIUM

### AP-13 — Queries N+1
- **Sinais:** query dentro de `for`/`forEach` sobre resultado de outra query
  (`for row in rows: cursor.execute("SELECT ... WHERE id = " + row[...])`,
  `Model.query.get(t.user_id)` no loop, `len(u.tasks)` lazy em loop, `db.get` aninhado em `forEach`);
  várias `COUNT(*)` separadas que poderiam ser um `GROUP BY`.
- **Por que importa:** 1 + N (ou 1 + N + N·M) idas ao banco; degrada linearmente com o volume.
- **Fix:** **P-06** (JOIN / eager loading / agregação).

### AP-14 — Validação de entrada ausente ou inconsistente
- **Sinais:** campos usados sem checar tipo (`priority < 1` com string → `TypeError` 500),
  `request.get_json()` usado sem checar `None`, validações diferentes entre create e update,
  regras de validação duplicadas em várias rotas, e-mail sem unicidade.
- **Por que importa:** entradas inválidas viram erro 500 ou dados corrompidos.
- **Fix:** **P-16** (camada de validação única por recurso).

### AP-15 — Código duplicado
- **Sinais:** o mesmo bloco (conversão row→dict, cálculo de "overdue", listas de status válidos,
  checagem de e-mail) repetido em ≥ 2 lugares; funções quase idênticas (`get_pedidos_usuario` vs `get_todos_pedidos`).
- **Por que importa:** correções precisam ser replicadas; divergências silenciosas.
- **Fix:** **P-07**/**P-13** (extrair função/método único, constantes compartilhadas).

### AP-16 — Tratamento de erros ausente ou descentralizado
- **Sinais:** `try/except Exception` repetido em todo handler devolvendo `str(e)` ao cliente;
  `except:` nu (bare except); erros de callback ignorados (`(err) => { res.send(...) }` sem checar `err`);
  respostas de erro em formatos diferentes (texto puro vs JSON).
- **Por que importa:** vaza detalhes internos, engole falhas reais, contrato de erro imprevisível.
- **Fix:** **P-05** (exceções de domínio + error handler central).

### AP-17 — Uso de APIs deprecated
- **Sinais:** compare o código com a tabela abaixo **considerando as versões do manifesto**.

| Stack | API obsoleta | Substituto moderno |
|---|---|---|
| Python ≥ 3.12 | `datetime.utcnow()` / `datetime.utcfromtimestamp()` | `datetime.now(timezone.utc)` |
| SQLAlchemy ≥ 2.0 | `Model.query.get(id)` (`Query.get`, "legacy") | `db.session.get(Model, id)` |
| SQLAlchemy ≥ 2.0 | `Model.query.filter_by(...)` estilo 1.x (legado, ainda suportado) | `db.session.execute(db.select(Model).filter_by(...))` |
| Flask ≥ 2.3 | `@app.before_first_request`, `flask.json.JSONEncoder`, `app.json_encoder` | inicialização no factory; `app.json` provider |
| Python ≥ 3.12/3.13 | `distutils`, `imp`, `cgi`, `pkg_resources` | `setuptools`/`importlib`/`email`/`importlib.metadata` |
| Node.js | `new Buffer(x)` | `Buffer.from(x)` / `Buffer.alloc(n)` |
| Node.js | `url.parse()`, `querystring` | `new URL()`, `URLSearchParams` |
| Node.js | `crypto.createCipher()` | `crypto.createCipheriv()` |
| Node.js | `fs.exists()` | `fs.access()` / `fs.existsSync()` |
| Express 4→5 | `req.param()`, `res.send(status)`, `res.json(obj, status)`, `app.del()` | `req.params/query/body`, `res.sendStatus()`, `res.status(s).json(obj)`, `app.delete()` |
| Express | pacote `body-parser` separado | `express.json()` / `express.urlencoded()` |
| npm | pacote `request` | `fetch` nativo (Node ≥ 18) |

- **Por que importa:** quebra em upgrades, warnings em runtime, comportamento sutilmente errado (datas naive).
- **Fix:** **P-12**. Se nenhuma ocorrer, registre no relatório "Deprecated APIs: none detected" com as versões verificadas.

### AP-18 — Callback hell / controle assíncrono manual
- **Sinais:** ≥ 3 níveis de callbacks aninhados, contadores manuais de pendências
  (`pending--; if (pending === 0) res.json(...)`), `const self = this` para escapar de `function`.
- **Por que importa:** ordem de resposta não determinística, erros ignorados, risco de responder duas vezes.
- **Fix:** **P-10** (promises + async/await).

### AP-19 — Integridade referencial ausente (dados órfãos)
- **Sinais:** `DELETE` do pai sem tratar filhos (matrículas/pagamentos/tarefas), FKs sem
  `ON DELETE`, comentários/mensagens admitindo dados "sujos".
- **Por que importa:** relatórios inconsistentes, registros apontando para entidades inexistentes.
- **Fix:** **P-09** (exclusão em cascata dentro de transação).

### AP-20 — Responsabilidade no módulo errado
- **Sinais:** rotas de um recurso dentro do arquivo de outro (ex.: CRUD de categorias em
  `report_routes`), helpers de validação que ninguém usa enquanto as rotas reimplementam a regra,
  side effects (e-mail/SMS) disparados direto do controller.
- **Por que importa:** dificulta descoberta e coesão do módulo.
- **Fix:** **P-03**/**P-07** (mover para o módulo do recurso/service).

---

## LOW

### AP-21 — Magic numbers / strings
- **Sinais:** literais de regra espalhados: faixas de desconto (`> 10000`, `* 0.1`), status
  (`'pending'`, `'aprovado'`), limites (`len(x) < 3`, `> 200`), regra de cartão (`startsWith("4")`), cores default.
- **Fix:** **P-13** (constantes/enum nomeados num único módulo).

### AP-22 — Nomenclatura ruim
- **Sinais:** variáveis de 1–2 letras fora de loops curtos (`u`, `e`, `p`, `cc`, `cid`), nomes
  numerados (`cursor2`, `cursor3`), nomes enganosos (`badCrypto`, `AppManager`), sombra de builtins (`id`, `type`).
- **Fix:** renomear ao extrair (P-03/P-07).

### AP-23 — `print` / `console.log` como logging
- **Sinais:** `print(...)`, `console.log(...)` em código de produção para eventos e erros.
  `grep -rnE "(^|[^A-Za-z_.])print\(|console\.log\(" .` (o prefixo evita falsos positivos como `Blueprint(`;
  scripts de CLI como `seed.py` podem usar `print` legitimamente).
- **Fix:** **P-15** (logger com níveis).

### AP-24 — Imports não usados / código morto
- **Sinais:** `import os, sys, json, time` sem uso; funções/constantes nunca referenciadas;
  exports não consumidos (`totalRevenue`).
  `python3 -m pyflakes .` / `npx eslint --rule 'no-unused-vars: error'` ou leitura.
- **Fix:** remover durante a refatoração.

### AP-25 — Condicionais verbosas / aninhamento desnecessário
- **Sinais:** `if cond: return True else: return False`; 3+ `if` aninhados para uma expressão booleana.
- **Fix:** retornar a expressão diretamente; guard clauses.

---

## Resumo do catálogo

| ID | Anti-pattern | Severidade | Playbook |
|---|---|---|---|
| AP-01 | Credenciais hardcoded | CRITICAL | P-01 |
| AP-02 | SQL Injection | CRITICAL | P-02 |
| AP-03 | God Class / God File | CRITICAL | P-03 |
| AP-04 | Endpoint admin perigoso | CRITICAL | P-14 |
| AP-05 | Senhas inseguras | CRITICAL | P-04 |
| AP-06 | Exposição de dados sensíveis | CRITICAL | P-11 |
| AP-07 | Fat Controller | HIGH | P-07 |
| AP-08 | Estado global mutável | HIGH | P-08 |
| AP-09 | Acoplamento sem DI | HIGH | P-08 |
| AP-10 | Config insegura (debug) | HIGH | P-01 |
| AP-11 | Token falso/previsível | HIGH | P-14 |
| AP-12 | Escrita sem transação | HIGH | P-09 |
| AP-13 | N+1 queries | MEDIUM | P-06 |
| AP-14 | Validação ausente | MEDIUM | P-16 |
| AP-15 | Duplicação | MEDIUM | P-07/P-13 |
| AP-16 | Erros descentralizados | MEDIUM | P-05 |
| AP-17 | APIs deprecated | MEDIUM | P-12 |
| AP-18 | Callback hell | MEDIUM | P-10 |
| AP-19 | Dados órfãos | MEDIUM | P-09 |
| AP-20 | Responsabilidade no lugar errado | MEDIUM | P-03/P-07 |
| AP-21 | Magic numbers | LOW | P-13 |
| AP-22 | Nomenclatura ruim | LOW | P-03 |
| AP-23 | print como log | LOW | P-15 |
| AP-24 | Código morto | LOW | — |
| AP-25 | Condicionais verbosas | LOW | — |
