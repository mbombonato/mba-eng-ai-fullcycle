<details>
<summary>Phase 1 — Project Analysis (contexto)</summary>

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js — versão não fixada em "engines"; validado em Node 22)
Framework:     Express 4.18.2 (^4.18.2 → 4.22.1 resolvido no package-lock)
Dependencies:  sqlite3 5.1.7
Database:      SQLite em memória (':memory:') via driver sqlite3 (API de callbacks), schema + seed no boot
Domain:        LMS API com fluxo de checkout (cursos, matrículas, pagamentos, usuários, auditoria)
Architecture:  Monolito sem camadas — classe AppManager concentra conexão, schema, seed, rotas,
               regra de pagamento e relatório; utils.js mistura config com segredos, cache global e hash
Entry point:   src/app.js (npm start → node src/app.js, porta 3000)
Source files:  3 files analyzed (~180 lines)
DB tables:     users, courses, enrollments, payments, audit_logs
Endpoints:     3 routes
================================
```

| METHOD | PATH | HANDLER | FILE:LINE |
|---|---|---|---|
| POST | /api/checkout | AppManager.setupRoutes (anônimo) | src/AppManager.js:28 |
| GET | /api/admin/financial-report | AppManager.setupRoutes (anônimo) | src/AppManager.js:80 |
| DELETE | /api/users/:id | AppManager.setupRoutes (anônimo) | src/AppManager.js:131 |

</details>

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js) + Express 4.22.1
Files:   3 analyzed | ~180 lines of code
Date:    2026-11-09
```

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 5 |
| HIGH | 4 |
| MEDIUM | 5 |
| LOW | 4 |
| **Total** | **18** |

## Findings

### F-01 [CRITICAL] God Class: AppManager faz banco, schema, seed, rotas, pagamento e relatório (AP-03)
- **File:** `src/AppManager.js:1-141`
- **Description:** A classe instancia o banco (linha 7), cria tabelas e seed (10-23), registra todas as rotas (25-137) e implementa dentro dos handlers a regra de pagamento (45-48), a matrícula, a auditoria (57) e o relatório financeiro (80-129).
- **Impact:** Viola SRP por completo; nenhuma regra é testável sem subir o Express e o SQLite; qualquer mudança arrisca todo o sistema.
- **Recommendation:** Decompor em config, database, models por tabela, services (checkout, pagamento, relatório), controllers, routes e middlewares, ligados num composition root → Playbook P-03

### F-02 [CRITICAL] Credenciais e chave de gateway hardcoded (AP-01)
- **File:** `src/utils.js:1-7`
- **Description:** `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"`, `dbUser` e `smtpUser` fixos no código, junto da porta.
- **Impact:** Chave **live** do gateway de pagamento e senha de banco de produção versionadas; impossível rotacionar por ambiente.
- **Recommendation:** Módulo `config` lendo `process.env` (`process.loadEnvFile()` para `.env`), `.env.example` sem valores; remover chaves não usadas → Playbook P-01

### F-03 [CRITICAL] Número de cartão e chave do gateway gravados em log (AP-06)
- **File:** `src/AppManager.js:45`
- **Description:** `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` registra o PAN completo e a chave secreta a cada checkout.
- **Impact:** Violação direta de PCI-DSS; qualquer pessoa com acesso aos logs obtém cartões e a chave do gateway.
- **Recommendation:** Logar apenas os 4 últimos dígitos e nunca a chave → Playbook P-11

### F-04 [CRITICAL] Hash de senha caseiro, sem salt, e senha default (AP-05)
- **File:** `src/utils.js:17-23, src/AppManager.js:18, 68`
- **Description:** `badCrypto` repete base64 dos 2 primeiros caracteres e trunca em 10 caracteres (determinístico, sem salt, trivialmente reversível/colidível); usuário novo sem `pwd` recebe a senha `"123456"`; o seed grava `'123'` em texto puro.
- **Impact:** Senhas recuperáveis a partir do banco; contas criadas no checkout ficam com senha conhecida publicamente.
- **Recommendation:** `crypto.scryptSync` com salt aleatório (stdlib do Node), senha obrigatória para novos usuários → Playbook P-04

### F-05 [CRITICAL] Rotas administrativas e destrutivas sem autenticação (AP-04)
- **File:** `src/AppManager.js:80, 131-137`
- **Description:** `GET /api/admin/financial-report` (nomes de alunos e valores pagos) e `DELETE /api/users/:id` aceitam qualquer cliente anônimo.
- **Impact:** Vazamento de dados financeiros/pessoais e exclusão de usuários por qualquer pessoa.
- **Recommendation:** Middleware `requireAdmin` validando `X-Admin-Token` contra `ADMIN_TOKEN` com comparação em tempo constante → Playbook P-14

### F-06 [HIGH] Regra de negócio dentro dos handlers de rota (AP-07)
- **File:** `src/AppManager.js:28-78, 80-129`
- **Description:** O handler de checkout valida entrada, decide aprovação do pagamento, cria usuário, matrícula, pagamento e auditoria e grava cache; o handler do relatório agrega receita e alunos.
- **Impact:** Regras presas ao HTTP, impossíveis de reutilizar ou testar isoladamente.
- **Recommendation:** `CheckoutService`, `PaymentGateway` e `ReportService` chamados por controllers finos → Playbook P-07

### F-07 [HIGH] Estado global mutável compartilhado (AP-08)
- **File:** `src/utils.js:9-15, 25`
- **Description:** `let globalCache = {}` cresce sem limite a cada checkout (`logAndCache`) e é exportado para mutação; `let totalRevenue = 0` exportado como estado global.
- **Impact:** Vazamento de memória, acoplamento oculto entre módulos, estado que não sobrevive a múltiplas instâncias.
- **Recommendation:** Remover o cache não utilizado (nada lê dele) e manter estado apenas em instâncias injetadas → Playbook P-08

### F-08 [HIGH] Acoplamento forte sem injeção de dependência (AP-09)
- **File:** `src/AppManager.js:5-8, src/app.js:8-10`
- **Description:** O construtor cria a própria conexão `new sqlite3.Database(':memory:')`; `app.js` depende da classe concreta que também conhece o Express.
- **Impact:** Impossível substituir o banco em testes ou trocar a persistência; viola DIP.
- **Recommendation:** Composition root `createApp({ db, config })` criando e injetando models/services/controllers → Playbook P-08

### F-09 [HIGH] Checkout grava matrícula, pagamento e auditoria sem transação (AP-12)
- **File:** `src/AppManager.js:50-62`
- **Description:** Três `INSERT` encadeados em callbacks independentes; falha no pagamento deixa matrícula sem pagamento; o erro do `INSERT` de auditoria é ignorado (linha 57).
- **Impact:** Matrículas "pagas" sem registro financeiro e trilha de auditoria incompleta.
- **Recommendation:** Executar as escritas do checkout em `BEGIN/COMMIT/ROLLBACK` serializado → Playbook P-09

### F-10 [MEDIUM] Queries N+1 no relatório financeiro (AP-13)
- **File:** `src/AppManager.js:83-128`
- **Description:** Para cada curso, 1 query de matrículas; para cada matrícula, 1 query de usuário e 1 de pagamento (1 + C + 2E consultas).
- **Impact:** Tempo de resposta cresce linearmente com o número de matrículas.
- **Recommendation:** Uma única query com `LEFT JOIN` courses × enrollments × users × payments e agrupamento em memória → Playbook P-06

### F-11 [MEDIUM] Callback hell com contadores manuais (AP-18)
- **File:** `src/AppManager.js:26, 37-77, 86-122`
- **Description:** Até 5 níveis de callbacks aninhados, `const self = this` para escapar do `function`, contadores `coursesPending`/`enrPending` decidindo quando responder.
- **Impact:** Ordem dos cursos no relatório não determinística, risco de responder duas vezes ou nunca responder.
- **Recommendation:** Wrapper promisificado do sqlite3 + async/await → Playbook P-10

### F-12 [MEDIUM] Erros ignorados e tratamento descentralizado (AP-16)
- **File:** `src/AppManager.js:38, 41, 51, 55, 57, 92-93, 104-106, 133-135`
- **Description:** Vários callbacks ignoram `err` (ex.: linha 92 lê `enrollments.length` sem checar `err` — um erro de banco derruba o processo com `TypeError`; linha 133 responde sucesso mesmo com erro); cada rota devolve erros em texto puro com mensagens diferentes.
- **Impact:** Falhas silenciosas, possível crash do processo, contrato de erro imprevisível.
- **Recommendation:** Classes de erro de domínio + middleware de erro central do Express e `asyncHandler` → Playbook P-05

### F-13 [MEDIUM] Exclusão de usuário deixa matrículas e pagamentos órfãos (AP-19)
- **File:** `src/AppManager.js:131-137`
- **Description:** `DELETE FROM users` sem tratar `enrollments`/`payments` — a própria resposta admite "as matrículas e pagamentos ficaram sujos no banco"; usuário inexistente também retorna 200.
- **Impact:** Relatórios com alunos "Unknown" e dados financeiros inconsistentes.
- **Recommendation:** Excluir pagamentos → matrículas → usuário na mesma transação; 404 para inexistente → Playbook P-09

### F-14 [MEDIUM] Validação de entrada mínima (AP-14)
- **File:** `src/AppManager.js:29-35`
- **Description:** Só verifica presença de `usr`, `eml`, `c_id`, `card`; não valida formato de e-mail, tipo de `c_id`, formato do cartão, e `pwd` é opcional mesmo para novos usuários.
- **Impact:** Dados inválidos persistidos; usuários criados com senha default.
- **Recommendation:** Função de parsing/validação única do payload de checkout → Playbook P-16

### F-15 [LOW] Nomenclatura ruim (AP-22)
- **File:** `src/AppManager.js:4, 29-33, 52, src/utils.js:17`
- **Description:** Variáveis `u`, `e`, `p`, `cid`, `cc`, `enrId`; nomes `AppManager` (genérico) e `badCrypto`.
- **Impact:** Leitura difícil e intenção obscura.
- **Recommendation:** Nomes de domínio (`name`, `email`, `courseId`, `cardNumber`) ao extrair camadas; o contrato de entrada (`usr`, `eml`...) é mantido e mapeado no controller → Playbook P-03

### F-16 [LOW] Magic numbers e strings de regra (AP-21)
- **File:** `src/AppManager.js:46, 48, 108, src/utils.js:6, 19`
- **Description:** Regra de aprovação `cc.startsWith("4")`, status `"PAID"`/`"DENIED"` literais, `10000` iterações, porta `3000`.
- **Impact:** Regras de negócio escondidas e duplicadas.
- **Recommendation:** Constantes nomeadas (`PAYMENT_STATUS`, `APPROVED_CARD_PREFIX`) → Playbook P-13

### F-17 [LOW] `console.log` como logging (AP-23)
- **File:** `src/AppManager.js:45, src/utils.js:13, src/app.js:13`
- **Description:** Logs sem nível nem formato.
- **Impact:** Sem controle de verbosidade; dados sensíveis misturados (ver F-03).
- **Recommendation:** Logger mínimo com níveis → Playbook P-15

### F-18 [LOW] Código morto e imports não usados (AP-24)
- **File:** `src/AppManager.js:2, src/utils.js:2-3, 5, 9-10, 25`
- **Description:** `totalRevenue` importado e nunca usado; `dbUser`, `dbPass`, `smtpUser` nunca lidos; `globalCache` só é escrito.
- **Impact:** Ruído e segredos mantidos sem necessidade.
- **Recommendation:** Remover durante a refatoração.

## Deprecated APIs

none detected — verificado contra Node.js 22 (sem `new Buffer`, `url.parse`, `crypto.createCipher`,
`fs.exists`), Express 4.22.1 (sem `req.param`, `res.send(status)`, `res.json(obj, status)`, `app.del`,
`body-parser` avulso — já usa `express.json()`) e sqlite3 5.1.7.

## Proposed target structure

```
ecommerce-api-legacy/
├── .env.example
├── src/
│   ├── server.js                 # entry point (npm start)
│   ├── app.js                    # composition root: createApp({ db, config })
│   ├── config/{index.js, constants.js}
│   ├── database/{connection.js, schema.js}
│   ├── models/{userModel, courseModel, enrollmentModel, paymentModel, auditLogModel}.js
│   ├── services/{paymentGateway, checkoutService, reportService, userService, passwordHasher}.js
│   ├── controllers/{checkoutController, reportController, userController}.js
│   ├── views/routes.js
│   ├── middlewares/{errorHandler, requireAdmin, asyncHandler}.js
│   └── utils/{errors, logger}.js
└── tests/smoke.json
```

```
================================
Total: 18 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
