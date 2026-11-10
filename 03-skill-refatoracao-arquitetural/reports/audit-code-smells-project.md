<details>
<summary>Phase 1 — Project Analysis (contexto)</summary>

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (3.13.15 na .venv; versão não fixada no projeto)
Framework:     Flask 3.1.1 (Werkzeug 3.1.9)
Dependencies:  flask-cors 5.0.1
Database:      SQLite via driver nativo sqlite3 (SQL manual, conexão por request em flask.g), arquivo DATABASE_PATH (padrão loja.db)
Domain:        E-commerce API (produtos, usuários, pedidos/itens, relatório de vendas)
Architecture:  MVC / camadas completas — config isolada, models só com SQL parametrizado, services com regras,
               controllers finos, rotas declarativas, error handler central e DI no composition root (create_app)
Entry point:   app.py (python3 app.py, porta 5000 — HOST/PORT via ambiente)
Source files:  29 files analyzed (~964 lines)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Endpoints:     18 routes
================================
```

| METHOD | PATH | HANDLER | FILE:LINE |
|---|---|---|---|
| GET | / | SistemaController.index | src/views/routes.py:9 |
| GET | /health | SistemaController.health | src/views/routes.py:10 |
| GET | /produtos | ProdutoController.listar | src/views/routes.py:12 |
| GET | /produtos/busca | ProdutoController.pesquisar | src/views/routes.py:13 |
| GET | /produtos/<int:id> | ProdutoController.buscar | src/views/routes.py:14 |
| POST | /produtos | ProdutoController.criar | src/views/routes.py:15 |
| PUT | /produtos/<int:id> | ProdutoController.atualizar | src/views/routes.py:16 |
| DELETE | /produtos/<int:id> | ProdutoController.deletar | src/views/routes.py:17 |
| GET | /usuarios | UsuarioController.listar | src/views/routes.py:19 |
| GET | /usuarios/<int:id> | UsuarioController.buscar | src/views/routes.py:20 |
| POST | /usuarios | UsuarioController.criar | src/views/routes.py:21 |
| POST | /login | UsuarioController.login | src/views/routes.py:22 |
| POST | /pedidos | PedidoController.criar | src/views/routes.py:24 |
| GET | /pedidos | PedidoController.listar_todos | src/views/routes.py:25 |
| GET | /pedidos/usuario/<int:usuario_id> | PedidoController.listar_por_usuario | src/views/routes.py:26 |
| PUT | /pedidos/<int:pedido_id>/status | PedidoController.atualizar_status | src/views/routes.py:27 |
| GET | /relatorios/vendas | SistemaController.relatorio_vendas | src/views/routes.py:29 |
| POST | /admin/reset-db | require_admin(SistemaController.reset_database) | src/views/routes.py:32 |

</details>

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1
Files:   29 analyzed | ~964 lines of code
Date:    2026-11-10
```

> Contexto: este projeto já passou por uma refatoração MVC (commit `052e1aa`; auditoria original em
> `audit-project-1.md`). Este relatório audita o **estado atual**. Os problemas graves do original
> (SQL injection, `/admin/query`, senhas em texto puro, segredos hardcoded, God File) não aparecem mais.
> Os achados abaixo são residuais.

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 7 |
| LOW | 2 |
| **Total** | **10** |

## Findings

### F-01 [HIGH] Escritas e dados pessoais acessíveis sem autenticação (AP-04)
- **File:** `src/views/routes.py:15-17, 19-20, 25-27`, `src/controllers/usuario_controller.py:29-34`
- **Description:** Só `POST /admin/reset-db` exige credencial. Qualquer cliente anônimo pode criar,
  alterar e apagar produtos (`POST/PUT/DELETE /produtos`), mudar status de qualquer pedido
  (`PUT /pedidos/<id>/status`), listar todos os pedidos (`GET /pedidos`) ou os de outro usuário
  (`GET /pedidos/usuario/<id>`, IDOR) e listar e-mails de todos os usuários (`GET /usuarios`).
  O `POST /login` não emite nenhum token, então não existe forma de autorizar essas chamadas.
  O campo `tipo` (`admin`/`cliente`) é gravado mas nunca usado em decisão de acesso.
- **Impact:** Vandalismo do catálogo, cancelamento/aprovação indevida de pedidos, vazamento de PII
  (e-mails, histórico de compras — LGPD). Severidade ajustada de CRITICAL para HIGH: são operações
  em um registro por vez, sem execução arbitrária, e a rota destrutiva em massa já está protegida.
- **Recommendation:** `POST /login` passa a devolver token assinado com expiração
  (`itsdangerous.URLSafeTimedSerializer`, já instalado como dependência do Flask, assinado com
  `SECRET_KEY`); middlewares `require_auth` e `require_role("admin")` aplicados às mutações de
  catálogo/status e às listagens de usuários/pedidos; `GET /pedidos/usuario/<id>` limitado ao próprio
  usuário ou admin. Isso muda o contrato por motivo de segurança → Playbook P-14

### F-02 [MEDIUM] Seed cria contas com senhas conhecidas em qualquer ambiente (AP-01)
- **File:** `src/database/schema.py:55-59, 68-76`
- **Description:** `init_db` popula `admin@loja.com`/`admin123`, `joao@email.com`/`123456` e
  `maria@email.com`/`senha123` sempre que `produtos` está vazia. Isso vale para qualquer banco novo,
  produção incluída, e não há flag que desligue. As senhas são gravadas com hash, mas os valores em claro
  estão no código versionado.
- **Impact:** Quem lê o repositório (público) consegue logar como "Admin". Severidade ajustada de
  CRITICAL para MEDIUM porque hoje `tipo=admin` não concede privilégio (rotas admin usam
  `X-Admin-Token`). Se F-01 for corrigido com papéis, sobe para CRITICAL.
- **Recommendation:** Seed de demonstração só com `SEED_DEMO_DATA=1` (default desligado, lido em
  `Settings`) e nunca com usuário `admin` de senha fixa → Playbook P-01

### F-03 [MEDIUM] Tipos não validados em usuário, login e produto geram 500 (AP-14)
- **File:** `src/controllers/validators.py:34, 53, 65-72, 75-80`, `src/models/usuario_model.py:48`
- **Description:** `validate_novo_usuario` não checa o tipo de `nome` e `senha`, `validate_login`
  não checa `email`/`senha` e `validate_produto` aceita `descricao` de qualquer tipo. Reproduzido
  com o test client:
  `POST /usuarios {"senha": 123}` → 500; `POST /usuarios {"nome": ["a"]}` → 500;
  `POST /login {"senha": 123456}` → 500 (`senha.encode` / `check_password_hash` com int);
  `POST /login {"email": ["a"]}` → 500; `POST /produtos {"descricao": {"a": 1}}` → 500.
  Também não há tamanho mínimo de senha (`"senha": "1"` é aceita, 201).
- **Impact:** Erro interno no lugar de 400, com stacktrace no log a cada requisição malformada.
  Senhas triviais ficam permitidas.
- **Recommendation:** Exigir `str` não vazia em `nome`/`email`/`senha`/`descricao`; definir
  `SENHA_MIN` em `config/constants.py` → Playbook P-16

### F-04 [MEDIUM] Unicidade de e-mail só na aplicação e sensível a maiúsculas (AP-14)
- **File:** `src/database/schema.py:17-24` (coluna `email TEXT` na linha 20, sem `UNIQUE`),
  `src/controllers/usuario_controller.py:24-25`, `src/models/usuario_model.py:24-27`
- **Description:** A regra "e-mail já cadastrado" é um `SELECT` seguido de `INSERT` no controller,
  sem constraint no banco e com comparação exata. Reproduzido: `JOAO@email.com` é aceito (201) com
  `joao@email.com` já cadastrado. Duas requisições simultâneas também passam pela checagem.
- **Impact:** Contas duplicadas. O login por e-mail pega a primeira linha, e as demais ficam inacessíveis.
- **Recommendation:** Normalizar e-mail (`strip().lower()`), criar `UNIQUE INDEX ... (email COLLATE NOCASE)`
  e converter `sqlite3.IntegrityError` em `ConflictError` no model. A regra sai do controller
  → Playbook P-16 / P-07

### F-05 [MEDIUM] Sem integridade referencial: apagar produto deixa itens de pedido órfãos (AP-19)
- **File:** `src/database/schema.py:7-38`, `src/models/produto_model.py:62-65`, `src/views/serializers.py:30`
- **Description:** Nenhuma tabela declara `FOREIGN KEY`. `DELETE /produtos/<id>` apaga
  fisicamente o produto mesmo quando `itens_pedido` o referencia. Reproduzido: depois de apagar o
  produto 2, o pedido passa a exibir `"produto_nome": "Desconhecido"`. A coluna `ativo` (soft delete)
  existe e é serializada, mas nenhum código a altera nem filtra por ela.
- **Impact:** Histórico de pedidos perde a referência do produto. `pedidos.usuario_id` também
  aceita ids inexistentes se gravados por fora do service.
- **Recommendation:** Declarar FKs com `PRAGMA foreign_keys = ON` na conexão e trocar o delete
  físico por `ativo = 0`, com listagens filtrando `ativo = 1` (ou devolver 409 se o produto tiver
  pedidos) → Playbook P-09

### F-06 [MEDIUM] Valores monetários em float sem arredondamento (fora do catálogo)
- **File:** `src/services/pedido_service.py:36`, `src/database/schema.py:11, 29, 37`
- **Description:** `total = sum(preco_unitario * quantidade)` em `float` é gravado em coluna `REAL`
  e devolvido sem arredondar. Reproduzido: 3 × 89.90 → `"total": 269.70000000000005` na resposta
  de `POST /pedidos` e em `GET /pedidos`.
- **Impact:** Valores exibidos incorretos e erro acumulado em somas. O relatório só esconde isso
  porque arredonda no final.
- **Recommendation:** Calcular com `decimal.Decimal` e arredondar para 2 casas antes de gravar e
  responder (formato do campo continua número) → Playbook P-13 (regra de arredondamento em um único ponto)

### F-07 [MEDIUM] Exceções de domínio definidas no middleware HTTP (AP-20)
- **File:** `src/middlewares/error_handler.py:10-35`, `src/services/pedido_service.py:5`,
  `src/controllers/validators.py:5`, `src/controllers/produto_controller.py:5`, `src/controllers/usuario_controller.py:3`
- **Description:** `AppError`, `ValidationError`, `NotFoundError` etc. ficam no módulo do error
  handler Flask e carregam `status_code` HTTP. Por isso o service (`pedido_service.py:5`) importa da
  camada de middleware.
- **Impact:** A dependência fica invertida (services → middlewares HTTP), contrariando "services não
  conhecem HTTP". Reaproveitar o service fora do Flask (CLI, worker) arrasta o módulo web junto.
- **Recommendation:** Mover as exceções para `src/errors.py` (sem status HTTP) e deixar o mapeamento
  exceção → status só em `register_error_handlers` → Playbook P-05

### F-08 [MEDIUM] CORS liberado para qualquer origem por padrão (AP-10)
- **File:** `src/config/settings.py:19, 25`, `.env.example:8`, `src/app.py:34`
- **Description:** Sem `CORS_ORIGINS` definida, o default é `"*"`, e o próprio `.env.example`
  sugere `*`.
- **Impact:** Qualquer site pode chamar a API pelo navegador do usuário. Severidade ajustada de HIGH
  para MEDIUM: a origem é configurável e a API não usa cookies/sessão. O risco cresce quando F-01
  introduzir tokens.
- **Recommendation:** Default fail-closed (lista vazia = sem CORS) e `.env.example` com origem
  explícita (ex.: `http://localhost:3000`) → Playbook P-01

### F-09 [LOW] Controller acessa a camada de banco diretamente (AP-20)
- **File:** `src/controllers/sistema_controller.py:6, 12-14, 50`, `src/app.py:51`
- **Description:** `SistemaController` recebe o `connection_provider` e chama
  `database.schema.reset_db(conn)`, sem passar por model ou service. É o único controller que conhece
  a conexão.
- **Impact:** Quebra a regra de controllers sem acesso a dados e alarga a assinatura do construtor
  (6 dependências). Severidade ajustada de MEDIUM para LOW: é uma única operação administrativa.
- **Recommendation:** Criar `AdminService.reset_database()` (ou método no model) injetado no
  controller e retirar `connection_provider` do controller → Playbook P-07

### F-10 [LOW] Parâmetro `id` sombreia builtin nos handlers (AP-22)
- **File:** `src/controllers/produto_controller.py:26, 45, 51`, `src/controllers/usuario_controller.py:16`,
  `src/views/routes.py:14, 16, 17, 20`
- **Description:** Os handlers usam `id` (com `# noqa: A002`) porque as rotas declaram `<int:id>`.
- **Impact:** Legibilidade, e o lint fica suprimido em vez de corrigido.
- **Recommendation:** Renomear o conversor para `<int:produto_id>`/`<int:usuario_id>`. A URL pública
  não muda → Playbook P-03

## Verificações sem ocorrência (falsos positivos descartados)

- **AP-02:** os hits de `execute(f"...")` em `src/models/*.py:11, 17, 42, 43` e `src/database/schema.py:85`
  interpolam só constantes de colunas, cláusulas fixas montadas no código e nomes de tabela de
  uma tupla literal. Todo valor de usuário vai por placeholder `?`.
- **AP-03, AP-05, AP-06, AP-08, AP-09, AP-11, AP-12, AP-13, AP-16, AP-18, AP-23, AP-24, AP-25:** sem
  ocorrência. Senhas com `werkzeug.security` (migração de legado em `usuario_model.py:38-54`),
  serializers com whitelist, conexão por request em `flask.g`, DI em `create_app`, pedido + itens +
  estoque numa transação com baixa condicional, itens carregados em uma query, error handler
  central e `pyflakes` limpo.
- **AP-21:** os literais restantes (`'cliente'`, `'pendente'` como `DEFAULT` no DDL) estão no schema,
  não espalhados em regra de negócio.

## Deprecated APIs

none detected — verificado contra Python 3.13 (`datetime.utcnow`, `distutils`, `imp`, `cgi`,
`pkg_resources`) e Flask 3.1.1 / Werkzeug 3.1.9 (`before_first_request`, `JSONEncoder`,
`app.json_encoder`). Não usa SQLAlchemy.

## Proposed target structure

O projeto já está em MVC. Seguindo `mvc-guidelines.md` ("Já em MVC: apenas corrigir findings
pontuais"), a proposta mantém a árvore e faz só estes acréscimos/mudanças:

```
app.py
src/
├── app.py                    # composition root (injeta AdminService/AuthService)
├── errors.py                 # NOVO — exceções de domínio sem HTTP (F-07)
├── config/
│   ├── settings.py           # + SEED_DEMO_DATA, CORS fail-closed, TOKEN_MAX_AGE (F-02, F-08, F-01)
│   └── constants.py          # + SENHA_MIN, CASAS_DECIMAIS (F-03, F-06)
├── database/
│   ├── connection.py         # + PRAGMA foreign_keys = ON (F-05)
│   └── schema.py             # FKs, UNIQUE email NOCASE, seed condicional (F-02, F-04, F-05)
├── models/                   # produto (soft delete), usuario (email normalizado, IntegrityError)
├── services/
│   ├── auth_service.py       # NOVO — emissão/validação de token assinado (F-01)
│   ├── admin_service.py      # NOVO — reset do banco (F-09)
│   └── pedido_service.py     # total com Decimal (F-06)
├── controllers/              # validators com checagem de tipo (F-03); rotas sem `id` (F-10)
├── views/                    # routes.py com require_auth/require_role (F-01)
└── middlewares/
    ├── auth.py               # + require_auth, require_role (F-01)
    └── error_handler.py      # só mapeia exceções → status (F-07)
tests/smoke.json              # + casos 401/403, tipos inválidos, e-mail duplicado com caixa
```

```
================================
Total: 10 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
