# Skill `refactor-arch` — Auditoria e Refatoração Arquitetural para MVC

Entrega do desafio **"Criação de Skills — Refatoração Arquitetural Automatizada"** (MBA Engenharia de
Software com IA — Full Cycle). O enunciado completo está em [`ENUNCIADO.md`](ENUNCIADO.md).

A skill `refactor-arch` (Claude Code) analisa um backend web (exercitada em Flask e Express, com heurísticas de detecção para outras stacks), gera um relatório de auditoria com
severidade e `arquivo:linha` exatos e — **somente após confirmação humana** — refatora o projeto para
MVC, validando boot e endpoints. Ela foi aplicada aos três projetos legados deste repositório (ver "Nota sobre a execução registrada").

```
.
├── README.md                                  # este documento
├── ENUNCIADO.md                               # enunciado do desafio
├── code-smells-project/                       # Projeto 1 — Python/Flask (E-commerce) — refatorado
│   └── .claude/skills/refactor-arch/          # ← a skill (original)
├── ecommerce-api-legacy/                      # Projeto 2 — Node.js/Express (LMS + checkout) — refatorado
│   └── .claude/skills/refactor-arch/          # ← cópia idêntica
├── task-manager-api/                          # Projeto 3 — Python/Flask (Task Manager) — refatorado
│   └── .claude/skills/refactor-arch/          # ← cópia idêntica
└── reports/
    ├── audit-project-1.md                     # saída da Fase 2 (+ Fase 1 como contexto)
    ├── audit-project-2.md
    └── audit-project-3.md
```

---

## A) Análise Manual

Feita **antes** de escrever a skill, lendo todo o código e confirmando os problemas mais graves com
requisições reais contra as versões originais (baseline — ver seção C). Escala de severidade do
enunciado: CRITICAL (segurança grave / God Class), HIGH (violação forte de MVC/SOLID), MEDIUM
(duplicação, N+1, validação, padronização), LOW (legibilidade).

### Projeto 1 — `code-smells-project` (Python/Flask, E-commerce)

| # | Severidade | Problema | Onde | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | SQL Injection em praticamente todas as queries (concatenação de strings) | `models.py:28, 47-50, 109-111, 289-297…` | Confirmado: `POST /login` com `email = "admin@loja.com' --"` **loga como admin** sem senha; produto com aspas (`Copo d'água`) quebra com 500 |
| 2 | CRITICAL | `POST /admin/query` executa SQL arbitrário e `POST /admin/reset-db` apaga tudo, sem autenticação | `app.py:47-78` | Qualquer cliente anônimo exfiltra ou destrói o banco inteiro |
| 3 | CRITICAL | Senhas em texto puro + `senha` devolvida em `GET /usuarios`; `/health` devolve `secret_key` | `models.py:83, 99, 126-129`, `controllers.py:285-289` | Vazamento direto de credenciais e do segredo da aplicação |
| 4 | CRITICAL | `SECRET_KEY` hardcoded | `app.py:7` | Segredo versionado, impossível rotacionar por ambiente |
| 5 | CRITICAL | God File: `models.py` mistura SQL, regras (estoque, desconto) e formatação de 4 domínios | `models.py:1-314` | Viola SRP; nada é testável isoladamente |
| 6 | HIGH | `debug=True` + `host="0.0.0.0"` fixos | `app.py:8, 88` | Debugger do Werkzeug exposto = execução remota de código |
| 7 | HIGH | Conexão SQLite global compartilhada entre threads (`check_same_thread=False`) | `database.py:4-11` | Estado global mutável, condições de corrida |
| 8 | HIGH | Pedido gravado em várias etapas sem transação; quantidade negativa **aumenta** o estoque | `models.py:133-169` | Inconsistência de estoque e financeira |
| 9 | MEDIUM | N+1: para cada pedido busca itens, para cada item busca o produto | `models.py:171-233` | 1 + N + N·M queries |
| 10 | MEDIUM | 17 blocos `except Exception: return {"erro": str(e)}, 500` | `controllers.py` (16) e `app.py` (1) | Vaza detalhes internos; erros de entrada viram 500 |
| 11 | MEDIUM | Validação duplicada e divergente entre criar/atualizar produto | `controllers.py:28-50` vs `72-90` | Update aceita categoria inválida |
| 12 | LOW | `print` como log (inclusive e-mails de login) | `controllers.py` (14×), `app.py` | Sem níveis; dados pessoais em stdout |
| 13 | LOW | Magic numbers de desconto (`10000`, `0.1`, `5000`…) e listas de status/categorias literais | `models.py:257-262`, `controllers.py:52, 242` | Regras de negócio escondidas |
| 14 | LOW | Sombra do builtin `id`, `cursor2`/`cursor3`, imports não usados | `models.py`, `database.py:2` | Legibilidade |

### Projeto 2 — `ecommerce-api-legacy` (Node.js/Express, LMS com checkout)

| # | Severidade | Problema | Onde | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | God Class `AppManager`: conexão, schema, seed, rotas, pagamento e relatório | `src/AppManager.js:1-141` | Nenhuma regra testável; qualquer mudança afeta tudo |
| 2 | CRITICAL | Chave **live** do gateway e senha de banco hardcoded | `src/utils.js:1-7` | Segredos de produção no repositório |
| 3 | CRITICAL | Log do **número do cartão completo** e da chave do gateway | `src/AppManager.js:45` | Violação de PCI-DSS |
| 4 | CRITICAL | "Hash" caseiro (base64 truncado, sem salt) e senha default `123456` | `src/utils.js:17-23`, `AppManager.js:68` | Senhas recuperáveis/conhecidas |
| 5 | CRITICAL | Relatório financeiro e `DELETE /api/users/:id` sem autenticação | `AppManager.js:80, 131` | Qualquer um lê dados financeiros e apaga usuários |
| 6 | HIGH | Checkout (matrícula + pagamento + auditoria) sem transação; erro de auditoria ignorado | `AppManager.js:50-62` | Matrícula sem pagamento registrado |
| 7 | HIGH | Estado global mutável (`globalCache` que só cresce, `totalRevenue`) | `src/utils.js:9-15` | Vazamento de memória, acoplamento oculto |
| 8 | MEDIUM | N+1 + callback hell com contadores manuais no relatório | `AppManager.js:83-128` | 1 + C + 2E queries; ordem não determinística |
| 9 | MEDIUM | Erros de callback ignorados (`enrollments.length` sem checar `err` derruba o processo) | `AppManager.js:92-93, 133` | Crash e falhas silenciosas |
| 10 | MEDIUM | Delete de usuário deixa matrículas/pagamentos órfãos (a própria resposta admite) | `AppManager.js:131-137` | Relatórios inconsistentes |
| 11 | LOW | Nomes `u`, `e`, `p`, `cid`, `cc`, `badCrypto`, `AppManager` | `AppManager.js:29-33` | Intenção obscura |
| 12 | LOW | Magic values: `cc.startsWith("4")`, `"PAID"`/`"DENIED"`, `10000` | `AppManager.js:46, 108`, `utils.js:19` | Regras escondidas |
| 13 | LOW | `console.log` como log; `totalRevenue`, `dbUser`, `smtpUser` nunca usados | vários | Ruído e segredos desnecessários |

### Projeto 3 — `task-manager-api` (Python/Flask, Task Manager com camadas parciais)

| # | Severidade | Problema | Onde | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | `SECRET_KEY` e senha SMTP hardcoded | `app.py:13`, `services/notification_service.py:7-10` | Segredos versionados |
| 2 | CRITICAL | Senhas com MD5 sem salt **e** hash devolvido em `GET /users/<id>`, `POST /users`, `PUT /users`, `/login` | `models/user.py:16-32` | Hash MD5 exposto é revertido em segundos |
| 3 | HIGH | Token de login `fake-jwt-token-<id>` | `routes/user_routes.py:210` | Qualquer um forja o token de qualquer usuário |
| 4 | HIGH | Blueprints fazem tudo (validação, regra, query, serialização); `services/` sem uso | `routes/*.py` | A estrutura de pastas "parece" em camadas, mas não é |
| 5 | HIGH | `debug=True`, `host='0.0.0.0'`, config fixa no entry point | `app.py:11-15, 34` | RCE via debugger, nada configurável |
| 6 | MEDIUM | N+1 em `GET /tasks`, `GET /users`, `/categories` e no resumo | `task_routes.py:14-59`, `report_routes.py:53-68…` | Escala linear com volume |
| 7 | MEDIUM | APIs deprecated: `Model.query.get()` (16×) e `datetime.utcnow()` (~20×) | rotas e models | Quebra em upgrades (SQLAlchemy 2.x, Python 3.12+) |
| 8 | MEDIUM | Cálculo de "overdue" copiado em 6 lugares enquanto `Task.is_overdue()` existe sem uso | `task_routes.py`, `user_routes.py`, `report_routes.py` | Duplicação e divergência |
| 9 | MEDIUM | `priority: "alta"` → `TypeError` → **500** (confirmado no baseline); 12 `except:` nus | `task_routes.py:113` | Validação de tipo ausente, falhas engolidas |
| 10 | MEDIUM | CRUD de categorias dentro de `report_routes`; delete de categoria deixa tasks órfãs | `report_routes.py:157-223` | Coesão e integridade |
| 11 | LOW | `print` como log; imports não usados; `marshmallow`/`requests` sem uso | vários | Ruído |
| 12 | LOW | Magic numbers (3/200, 1–5, senha mínima 4) e condicionais `if x: return True else: return False` | `task_routes.py`, `models/*.py` | Legibilidade |

---

## B) Construção da Skill

### Estrutura

```
.claude/skills/refactor-arch/
├── SKILL.md                              # o "prompt": 3 fases, regras invioláveis, formatos de saída
├── references/
│   ├── project-analysis.md               # Fase 1 — detecção de linguagem/framework/banco/rotas/domínio/arquitetura
│   ├── anti-patterns-catalog.md          # Fase 2 — 25 anti-patterns com sinais de detecção (grep) e severidade
│   ├── report-template.md                # Fase 2 — formato padronizado do relatório
│   ├── mvc-guidelines.md                 # Fase 3 — camadas, responsabilidades, regra de dependência
│   ├── refactoring-playbook.md           # Fase 3 — 16 transformações com código antes/depois (Python e JS)
│   └── validation-guide.md               # Fase 3 — baseline, smoke test, re-scan, checklist
└── scripts/
    └── smoke_test.py                     # runner HTTP (stdlib) para baseline e validação
```

### Decisões de design

- **SKILL.md enxuto e procedural; conhecimento nas referências.** O SKILL.md diz *o que fazer e em que
  ordem* e aponta *quando* ler cada referência (progressive disclosure): a Fase 1 só precisa de
  `project-analysis.md`, a Fase 2 do catálogo + template, a Fase 3 do guideline + playbook + validação.
  Isso mantém o contexto pequeno e permite evoluir o conhecimento sem mexer no fluxo.
- **Frontmatter:** `disable-model-invocation: true` — uma skill que reescreve o projeto só deve rodar
  quando o usuário digita `/refactor-arch`, nunca por iniciativa do modelo; `allowed-tools` pré-autoriza as
  ferramentas de que a skill precisa (leitura, busca, shell e edição); `argument-hint` permite passar o caminho do relatório (`/refactor-arch ../reports/audit-project-1.md`).
- **Regras invioláveis explícitas:** Fases 1–2 somente leitura; pausa obrigatória com
  `Proceed with refactoring (Phase 3)? [y/n]` encerrando a resposta; todo finding com `arquivo:linha`;
  contrato público preservado (mudanças só por segurança, listadas); sem novas dependências se a stdlib resolve.
- **Formatos de saída fixos** (blocos `PHASE 1`, `ARCHITECTURE AUDIT REPORT`, `PHASE 3`) para que o resultado
  seja comparável entre projetos e verificável.
- **Validação baseada em evidência:** a Fase 3 começa capturando um **baseline** do app original com a mesma
  spec de smoke test usada depois. Falhas no baseline evidenciam os findings (ex.: bypass de login),
  e a mesma spec passando depois indica que os casos cobertos continuam respondendo como esperado. O `smoke_test.py` é stdlib pura para rodar
  em qualquer máquina com Python, independentemente da stack do projeto auditado.

### Catálogo de anti-patterns (25, com severidade distribuída)

| Severidade | Anti-patterns | Por que entraram |
|---|---|---|
| CRITICAL (6) | AP-01 credenciais hardcoded, AP-02 SQL Injection, AP-03 God Class, AP-04 endpoint admin perigoso, AP-05 senha insegura, AP-06 exposição de dados sensíveis | Todos encontrados na análise manual; são os que expõem dados ou impedem qualquer evolução |
| HIGH (6) | AP-07 Fat Controller, AP-08 estado global mutável, AP-09 acoplamento sem DI, AP-10 debug/config insegura, AP-11 token falso, AP-12 escrita sem transação | Violações MVC/SOLID e de robustez encontradas na análise manual (cada uma em pelo menos um dos projetos) |
| MEDIUM (8) | AP-13 N+1, AP-14 validação ausente, AP-15 duplicação, AP-16 erros descentralizados, **AP-17 APIs deprecated**, AP-18 callback hell, AP-19 dados órfãos, AP-20 responsabilidade no lugar errado | Performance, padronização e integridade |
| LOW (5) | AP-21 magic numbers, AP-22 nomes ruins, AP-23 print/console.log, AP-24 código morto, AP-25 condicionais verbosas | Legibilidade |

Cada entrada tem **sinais de detecção acionáveis** (ex.: "query dentro de `for`", regex de `execute(` com `+`),
"por que importa" e o **playbook** que corrige. AP-17 traz uma **tabela de APIs deprecated por stack e versão**
(Python 3.12+, SQLAlchemy 2.x, Flask 2.3+, Node, Express 4→5) com o substituto moderno.

### Como a skill é agnóstica de tecnologia

- A Fase 1 **detecta** a stack por manifesto + import (tabela para Python, Node, Go, Java, Ruby, PHP) em vez de presumir Flask.
- Catálogo e playbook descrevem **princípios** com exemplos em Python **e** JavaScript, e instruem a aplicar o equivalente idiomático em outras stacks.
- As guidelines MVC trazem uma **tabela de adaptação**: monolito → criar a árvore completa; camadas parciais → reaproveitar as pastas existentes e só extrair o que falta; já MVC → só corrigir findings.
- A validação é por HTTP (black-box), independente do framework.
- Na prática: a **mesma** pasta da skill (cópias idênticas, verificadas com `diff -r`) funcionou em Flask+SQL manual, Express+sqlite3 callbacks e Flask+SQLAlchemy.

### Desafios encontrados e como resolvi (iterações)

1. **Sinal de credenciais fraco.** A 1ª versão do grep (`(secret|_key)\s*=\s*"…"`) **não pegou**
   `app.config["SECRET_KEY"] = "..."` (chave entre colchetes), `paymentGatewayKey:` (camelCase) nem
   `self.email_password = '...'`. Ajustei o regex do AP-01 (`…\w*['"]?\]?\s*[:=]…` + `(pk|sk)_live_`) e
   validei que passou a detectar os 3 projetos.
2. **Falsos positivos no re-scan.** O grep de SQL concatenado acusava `f"SELECT {COLUMNS} …"` (interpola só
   constantes do código) e o de `print(` acusava `Blueprint(`. Documentei no guia de validação/catálogo
   como distinguir (ler a ocorrência; regex com prefixo para `print`).
3. **Contrato × segurança.** Preservar 100% do contrato manteria vulnerabilidades (`/admin/query`, senha na resposta).
   Defini a regra: contrato de sucesso preservado; mudanças só por segurança, sempre listadas em
   "Contract changes" — e a spec de smoke test prova os dois lados (`forbid_keys`, `expect_status` 401/403).
4. **Projeto parcialmente organizado.** Reescrever o projeto 3 do zero seria fácil, mas errado. A guideline
   manda reaproveitar `models/` e `routes/` (rotas viram views finas) e acrescentar `controllers/`,
   `services/`, `config/`, `middlewares/` — o que manteve `python3 seed.py && python3 app.py` funcionando.
5. **Hashes legados.** Trocar MD5/texto puro por scrypt quebraria logins em bancos existentes. O playbook P-04
   inclui migração transparente no primeiro login válido.
6. **Ambiente:** não havia `npm` no PATH; as dependências do projeto 2 foram instaladas com `bun install --no-save`
   (sem alterar `package-lock.json`).

---

## C) Resultados

### Resumo das auditorias (Fase 2)

| Projeto | Stack detectada | Arquitetura detectada | CRITICAL | HIGH | MEDIUM | LOW | Total | Deprecated |
|---|---|---|---|---|---|---|---|---|
| 1 — code-smells-project | Python + Flask 3.1.1 | Monolito sem camadas (4 arquivos) | 6 | 5 | 4 | 4 | **19** | nenhuma (verificado) |
| 2 — ecommerce-api-legacy | Node.js + Express 4.22.1 | Monolito sem camadas (God Class) | 5 | 4 | 5 | 4 | **18** | nenhuma (verificado) |
| 3 — task-manager-api | Python + Flask 3.0.0 / Flask-SQLAlchemy 3.1.1 | Camadas parciais | 3 | 3 | 7 | 4 | **17** | `Query.get()` (16×), `datetime.utcnow()` (~20×) |


### Antes × depois

**Projeto 1 — code-smells-project**
```
ANTES                         DEPOIS
app.py        (88)            app.py                      # entry point fino
controllers.py(292)           .env.example
models.py     (314)           src/
database.py   (86)            ├── app.py                  # composition root: create_app()
requirements.txt              ├── config/{settings,constants}.py
                              ├── database/{connection,schema}.py
                              ├── models/{produto,usuario,pedido}_model.py
                              ├── services/{pedido,relatorio,notificacao}_service.py
                              ├── controllers/{produto,usuario,pedido,sistema}_controller.py + validators.py
                              ├── views/{routes,serializers}.py
                              └── middlewares/{error_handler,auth}.py
                              tests/smoke.json
```

**Projeto 2 — ecommerce-api-legacy**
```
ANTES                         DEPOIS
src/app.js        (14)        src/server.js               # entry point (npm start)
src/AppManager.js (141)       src/app.js                  # composition root: createApp({ db, config, logger })
src/utils.js      (25)        src/config/{index,constants}.js
api.http                      src/database/{connection,schema}.js   # wrapper promisificado + transações
package.json                  src/models/{user,course,enrollment,payment,auditLog}Model.js
                              src/services/{checkout,paymentGateway,report,user}Service.js + passwordHasher.js
                              src/controllers/{checkout,report,user}Controller.js
                              src/views/routes.js
                              src/middlewares/{errorHandler,requireAdmin,asyncHandler}.js
                              src/utils/{errors,logger}.js
                              .env.example, tests/smoke.json
```

**Projeto 3 — task-manager-api** (estrutura existente aproveitada)
```
ANTES                                   DEPOIS
app.py (config fixa + debug)            app.py              # create_app() + entry point
database.py                             config/{settings,constants}.py           (novo)
models/{task,user,category}.py          models/{task,user,category}.py           (scrypt, is_overdue, utcnow)
routes/task_routes.py   (299, gordo)    routes/{task,user,category,report,system}_routes.py  (finos)
routes/user_routes.py   (211, gordo)    controllers/{task,user,category,report,system}_controller.py + validators.py (novo)
routes/report_routes.py (223, + CRUD    services/{task,user,category,auth,report}_service.py  (novo; o antigo
                         de categorias)          notification_service.py, não usado e com senha fixa, foi removido)
services/notification_service.py        views/serializers.py                     (novo)
utils/helpers.py (código morto)         middlewares/error_handler.py             (novo)
seed.py                                 utils/clock.py, seed.py, .env.example, tests/smoke.json
```

### Logs de execução (validação)

Baseline (apps **originais**) × depois (apps **refatorados**), mesma spec `tests/smoke.json` de cada projeto:

| Projeto | Original | Refatorado | O que falhava no original |
|---|---|---|---|
| 1 | 29/36 | **36/36** | `secret_key` no `/health`, `senha` em `/usuarios` (2×), produto com aspas → 500, **login com `' --` → 200**, `/admin/query` aberto, reset sem token |
| 2 | 8/12 | **12/12** | novo usuário sem senha aceito (default `123456`), relatório e delete sem token, delete de inexistente → 200 |
| 3 | 32/37 | **37/37** | `priority: "alta"` → 500, hash `password` em 4 respostas |

A coluna "Original" foi medida localmente contra o código do repositório base, sem log versionado. A coluna "Refatorado" é reproduzível com os comandos da seção D.

Execução final (boot do zero com o comando de start documentado de cada projeto):

```
### Projeto 1 — code-smells-project (python3 app.py)
 * Serving Flask app 'src.app'
 * Debug mode: off
 * Running on http://127.0.0.1:5121
36/36 requisições OK
### Projeto 2 — ecommerce-api-legacy (npm start → node src/server.js)
2026-11-09T19:54:16.023Z [WARN] PAYMENT_GATEWAY_KEY não configurada (gateway em modo simulado)
2026-11-09T19:54:16.047Z [INFO] LMS API rodando na porta 5122
12/12 requisições OK
### Projeto 3 — task-manager-api (python3 seed.py && python3 app.py)
Seed concluído com sucesso!
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5123
37/37 requisições OK
```

Trecho do smoke test do projeto 1 refatorado (casos que falhavam no original e agora passam):

```
  ✓ POST   /produtos      -> 201  Cria produto com aspas (SQL injection quebrava)
  ✓ GET    /usuarios      -> 200  Lista usuários sem senha
  ✓ POST   /login         -> 401  Login com SQL injection (bypass no original)
  ✓ POST   /pedidos       -> 201  Cria pedido
  ✓ GET    /relatorios/vendas -> 200  Relatório de vendas
  ✓ POST   /admin/query   -> 404  Admin query arbitrária removida
  ✓ POST   /admin/reset-db -> 403  Reset do banco sem token é negado
  ✓ POST   /admin/reset-db -> 200  Reset do banco com token de admin
36/36 requisições OK
```

Além do smoke test, os projetos Python foram iniciados com `python3 -W error::DeprecationWarning` e os greps do catálogo foram refeitos para os findings CRITICAL/HIGH (verificação manual, sem log versionado).

### Checklist de validação

| Item | P1 | P2 | P3 |
|---|---|---|---|
| **Fase 1** — Linguagem detectada corretamente | ✅ | ✅ | ✅ |
| Framework detectado corretamente | ✅ Flask 3.1.1 | ✅ Express 4.x | ✅ Flask 3.0.0 + SQLAlchemy |
| Domínio descrito corretamente | ✅ E-commerce | ✅ LMS + checkout | ✅ Task Manager |
| Nº de arquivos condiz com a realidade | ✅ 4 | ✅ 3 | ✅ 15 |
| **Fase 2** — Relatório segue o template | ✅ | ✅ | ✅ |
| Cada finding com arquivo e linhas exatos | ✅ | ✅ | ✅ |
| Ordenado CRITICAL → LOW | ✅ | ✅ | ✅ |
| Mínimo de 5 findings | ✅ 19 | ✅ 18 | ✅ 17 |
| Detecção de APIs deprecated (se aplicável) | ✅ verificada, nenhuma | ✅ verificada, nenhuma | ✅ 2 APIs |
| Pausa e pede confirmação antes da Fase 3 | ⚠️ o relatório termina com a pergunta; a confirmação veio do orquestrador, não de um `y` interativo (ver nota final) | ⚠️ idem | ⚠️ idem |
| **Fase 3** — Estrutura segue MVC | ✅ | ✅ | ✅ |
| Config extraída (sem hardcoded) | ✅ `src/config` | ✅ `src/config` | ✅ `config/` |
| Models abstraem os dados | ✅ | ✅ | ✅ |
| Views/Routes separadas | ✅ `views/` | ✅ `views/routes.js` | ✅ `routes/` + `views/` |
| Controllers concentram o fluxo | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ | ✅ | ✅ |
| Entry point claro | ✅ `app.py` | ✅ `src/server.js` | ✅ `app.py` |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem | ✅ 36/36 requisições (exceto `/admin/query`, removido por segurança) | ✅ 12/12 requisições (rotas admin passaram a exigir token) | ✅ 37/37 requisições |

### Observações sobre o comportamento em stacks diferentes

- **Monolito Python (P1):** transformação mais ampla — árvore MVC completa em `src/`, com o `app.py` raiz
  reduzido a entry point para manter `python3 app.py`. O maior ganho foi de segurança (SQLi, admin, senhas).
- **Node/Express (P2):** além do MVC, a skill aplicou transformações específicas de runtime assíncrono
  (P-10 callbacks → async/await, `asyncHandler` porque o Express 4 não captura rejeições) e transações
  serializadas na conexão única. O relatório financeiro saiu de 1 + C + 2E queries para 1 `LEFT JOIN`,
  com saída idêntica e ordem determinística.
- **Camadas parciais (P3):** a skill **não** reescreveu do zero — preservou `models/` e `routes/`, extraiu
  controllers/services e removeu código morto. Aqui apareceram as APIs deprecated (a checagem é guiada pelas
  versões do manifesto, e nos outros dois projetos o relatório registra "none detected" com as versões verificadas).
- Os mesmos IDs de catálogo (AP-xx) e de playbook (P-xx) aparecem nos três relatórios, o que facilita comparar projetos.

### Mudanças intencionais de contrato

As mudanças de contrato feitas por segurança (ex.: remoção de `/admin/query`, rotas admin com token, senha fora das respostas) estão listadas no README de cada projeto.

---

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado (`claude --version`).
- Python 3.10+ (validado com 3.13) e Node.js 20.12+ (validado com 22.x) com npm.
- A skill já está em `.claude/skills/refactor-arch/` dentro de cada projeto (o Claude Code descobre skills do projeto automaticamente).

### Executar a skill

```bash
# Projeto 1
cd code-smells-project
claude "/refactor-arch ../reports/audit-project-1.md"

# Projeto 2
cd ../ecommerce-api-legacy
claude "/refactor-arch ../reports/audit-project-2.md"

# Projeto 3
cd ../task-manager-api
claude "/refactor-arch ../reports/audit-project-3.md"
```

Sem argumento, o relatório é salvo em `../reports/audit-<nome-do-projeto>.md`. A skill imprime a Fase 1,
gera o relatório da Fase 2 e para em `Proceed with refactoring (Phase 3)? [y/n]` — responda `y` para refatorar.

> Os projetos deste repositório **já estão refatorados**. Para reproduzir do zero, use os originais do
> [repositório base](https://github.com/devfullcycle/mba-ia-refactor-projects-skill) e copie a pasta
> `.claude/skills/refactor-arch/` para dentro de cada um.

### Validar a refatoração

```bash
SMOKE=.claude/skills/refactor-arch/scripts/smoke_test.py

# Projeto 1
cd code-smells-project && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
ADMIN_TOKEN=smoke DATABASE_PATH=/tmp/p1.db PORT=5111 .venv/bin/python app.py &
ADMIN_TOKEN=smoke python3 $SMOKE tests/smoke.json --base-url http://127.0.0.1:5111   # 36/36
kill %1

# Projeto 2
cd ../ecommerce-api-legacy && npm install
ADMIN_TOKEN=smoke PORT=3100 npm start &
ADMIN_TOKEN=smoke python3 $SMOKE tests/smoke.json --base-url http://127.0.0.1:3100   # 12/12
kill %1

# Projeto 3
cd ../task-manager-api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
DATABASE_URL=sqlite:////tmp/p3.db .venv/bin/python seed.py
DATABASE_URL=sqlite:////tmp/p3.db PORT=5113 .venv/bin/python app.py &
python3 $SMOKE tests/smoke.json --base-url http://127.0.0.1:5113                      # 37/37
kill %1
```

Use um banco novo a cada execução (a spec cria/remove registros e, no projeto 1, termina resetando o banco).

### Nota sobre a execução registrada

Os relatórios e refatorações deste repositório foram produzidos por um agente Claude Code seguindo o
`SKILL.md` literalmente (fases, formatos, referências e validação). A pausa da Fase 2 foi respeitada — o
relatório termina com a pergunta de confirmação — e a autorização para a Fase 3 veio da instrução do
orquestrador da tarefa, não de um `y` digitado interativamente.

Em 2026-11-10 a skill foi invocada de forma interativa (`/refactor-arch`) no `code-smells-project/` já
refatorado. Ela executou as Fases 1 e 2, gravou `reports/audit-code-smells-project.md` (10 findings
residuais) e parou na pergunta de confirmação. A resposta foi `n`, e nenhum arquivo do projeto foi
alterado. Essa execução mostra a pausa com um humano; não substitui os relatórios `audit-project-{1,2,3}.md`,
que são os do código original.
