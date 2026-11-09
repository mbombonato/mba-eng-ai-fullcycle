<details>
<summary>Phase 1 — Project Analysis (contexto)</summary>

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (3.13 no ambiente de validação; versão não fixada no projeto)
Framework:     Flask 3.0.0
Dependencies:  Flask-SQLAlchemy 3.1.1 (SQLAlchemy 2.x, não fixado), flask-cors 4.0.0,
               marshmallow 3.20.1, requests 2.31.0, python-dotenv 1.0.0 (as 3 últimas não são usadas)
Database:      SQLite via ORM Flask-SQLAlchemy, URI fixa 'sqlite:///tasks.db' (instance/tasks.db)
Domain:        Task Manager API (tasks, usuários, categorias, relatórios de produtividade)
Architecture:  Camadas parciais — existem models/, routes/, services/, utils/, mas os blueprints
               concentram validação, regras (atraso, estatísticas) e queries; services/ e utils/
               estão praticamente sem uso; config hardcoded no entry point
Entry point:   app.py (python seed.py && python app.py, porta 5000)
Source files:  15 files analyzed (~1158 lines, incluindo seed.py e 4 __init__.py)
DB tables:     users, tasks, categories
Endpoints:     22 routes
================================
```

| METHOD | PATH | HANDLER | FILE:LINE |
|---|---|---|---|
| GET | / | index | app.py:26 |
| GET | /health | health | app.py:22 |
| GET | /tasks | get_tasks | routes/task_routes.py:11 |
| GET | /tasks/<task_id> | get_task | routes/task_routes.py:65 |
| POST | /tasks | create_task | routes/task_routes.py:85 |
| PUT | /tasks/<task_id> | update_task | routes/task_routes.py:156 |
| DELETE | /tasks/<task_id> | delete_task | routes/task_routes.py:225 |
| GET | /tasks/search | search_tasks | routes/task_routes.py:240 |
| GET | /tasks/stats | task_stats | routes/task_routes.py:273 |
| GET | /users | get_users | routes/user_routes.py:10 |
| GET | /users/<user_id> | get_user | routes/user_routes.py:27 |
| POST | /users | create_user | routes/user_routes.py:42 |
| PUT | /users/<user_id> | update_user | routes/user_routes.py:92 |
| DELETE | /users/<user_id> | delete_user | routes/user_routes.py:134 |
| GET | /users/<user_id>/tasks | get_user_tasks | routes/user_routes.py:153 |
| POST | /login | login | routes/user_routes.py:185 |
| GET | /reports/summary | summary_report | routes/report_routes.py:12 |
| GET | /reports/user/<user_id> | user_report | routes/report_routes.py:103 |
| GET | /categories | get_categories | routes/report_routes.py:157 |
| POST | /categories | create_category | routes/report_routes.py:167 |
| PUT | /categories/<cat_id> | update_category | routes/report_routes.py:190 |
| DELETE | /categories/<cat_id> | delete_category | routes/report_routes.py:211 |

</details>

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1)
Files:   15 analyzed | ~1158 lines of code
Date:    2026-11-09
```

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 3 |
| HIGH | 3 |
| MEDIUM | 7 |
| LOW | 4 |
| **Total** | **17** |

## Findings

### F-01 [CRITICAL] Credenciais hardcoded: SECRET_KEY e senha SMTP (AP-01)
- **File:** `app.py:13, services/notification_service.py:7-10`
- **Description:** `app.config['SECRET_KEY'] = 'super-secret-key-123'` e `self.email_user = 'taskmanager@gmail.com'` / `self.email_password = 'senha123'` fixos no código.
- **Impact:** Segredos versionados permitem forjar assinaturas e usar a conta de e-mail; impossível rotacionar por ambiente.
- **Recommendation:** `config/settings.py` lendo variáveis de ambiente (python-dotenv já é dependência), `.env.example` sem valores → Playbook P-01

### F-02 [CRITICAL] Senhas com MD5 sem salt (AP-05)
- **File:** `models/user.py:27-32, routes/user_routes.py:64, 115`
- **Description:** `set_password` grava `hashlib.md5(pwd).hexdigest()`; `check_password` compara MD5. Senha mínima de 4 caracteres.
- **Impact:** MD5 sem salt é revertido por rainbow tables/força bruta em segundos — um vazamento expõe todas as senhas.
- **Recommendation:** `werkzeug.security.generate_password_hash` (scrypt + salt) com migração transparente dos hashes MD5 legados no próximo login → Playbook P-04

### F-03 [CRITICAL] Hash de senha exposto nas respostas da API (AP-06)
- **File:** `models/user.py:16-25, routes/user_routes.py:33, 85, 129, 209`
- **Description:** `User.to_dict()` inclui `password` e é devolvido por `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e `POST /login` (confirmado no baseline).
- **Impact:** Qualquer cliente obtém os hashes MD5 (ver F-02) e recupera as senhas.
- **Recommendation:** Serialização por whitelist na camada de view, sem `password` → Playbook P-11

### F-04 [HIGH] Token de autenticação falso e previsível (AP-11)
- **File:** `routes/user_routes.py:207-211`
- **Description:** O login devolve `'fake-jwt-token-' + str(user.id)` — sem assinatura nem expiração.
- **Impact:** Qualquer pessoa forja o token de qualquer usuário trocando o número.
- **Recommendation:** Token assinado com `SECRET_KEY` e expiração (`itsdangerous.URLSafeTimedSerializer`, já instalado com o Flask) em um `AuthService` → Playbook P-14

### F-05 [HIGH] Blueprints concentram validação, regras de negócio e queries (Fat Controller) (AP-07)
- **File:** `routes/task_routes.py:11-63, 85-154, 156-223, 273-299, routes/report_routes.py:12-101, 103-155, routes/user_routes.py:42-90, 92-132`
- **Description:** Cada rota valida campos, consulta o ORM, calcula atraso/estatísticas/produtividade e monta o JSON campo a campo; não há controllers nem services (a pasta `services/` só contém um serviço não utilizado).
- **Impact:** Regras impossíveis de reutilizar/testar sem HTTP; handlers de 50–90 linhas; a camada "routes" faz papel de view, controller e model.
- **Recommendation:** Manter `routes/` como views finas, criar `controllers/` (fluxo + validação) e `services/` (tarefas, usuários, relatórios, auth) → Playbook P-07, P-03

### F-06 [HIGH] Debug, bind público e configuração fixos no entry point (AP-10)
- **File:** `app.py:11-15, 34`
- **Description:** `app.run(debug=True, host='0.0.0.0', port=5000)`, URI do banco fixa, `CORS(app)` aberto, `db.create_all()` executado no import do módulo.
- **Impact:** Debugger do Werkzeug exposto na rede (execução remota de código); nada configurável por ambiente.
- **Recommendation:** Application factory `create_app(settings)` com flags vindas do ambiente e default seguro → Playbook P-01, P-08

### F-07 [MEDIUM] Queries N+1 em listagens e relatórios (AP-13)
- **File:** `routes/task_routes.py:14-59, 275-287, routes/user_routes.py:12-24, routes/report_routes.py:15-28, 53-68, 157-165`
- **Description:** `GET /tasks` faz `User.query.get` e `Category.query.get` por task; `GET /users` acessa `u.tasks` (lazy) por usuário; o resumo faz 9 `COUNT` separados + 1 query de tasks por usuário; `GET /categories` faz 1 `COUNT` por categoria.
- **Impact:** Número de queries cresce linearmente com tasks/usuários/categorias.
- **Recommendation:** `selectinload` para relacionamentos e agregações com `GROUP BY` → Playbook P-06

### F-08 [MEDIUM] Lógica duplicada enquanto o model já tem o método (AP-15)
- **File:** `routes/task_routes.py:17-39, 71-80, 110, 177, 283-287, routes/user_routes.py:162-180, routes/report_routes.py:34-36, 133-135, models/task.py:39, utils/helpers.py:75, 110`
- **Description:** O cálculo de "overdue" está copiado em 6 lugares (e `Task.is_overdue()` existe sem uso); a serialização manual de task duplica `to_dict()`; a lista de status válidos aparece em 5 lugares; validações de create e update são cópias divergentes.
- **Impact:** Correções precisam ser replicadas; comportamentos já divergem.
- **Recommendation:** Regra no model (`Task.is_overdue`), serializer único e validadores compartilhados → Playbook P-07, P-13

### F-09 [MEDIUM] APIs deprecated: `Query.get()` e `datetime.utcnow()` (AP-17)
- **File:** `routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227, routes/user_routes.py:29, 94, 136, 155, routes/report_routes.py:105, 192, 213` (Query.get); `models/task.py:15-16, 52, models/user.py:14, models/category.py:11, routes/task_routes.py:31, 72, 215, 285, routes/user_routes.py:172, routes/report_routes.py:35, 42, 45, 71, 133, utils/helpers.py:38, services/notification_service.py:35, seed.py:66-74` (utcnow)
- **Description:** `Model.query.get(id)` é API legada no SQLAlchemy 2.x; `datetime.utcnow()` é deprecated desde o Python 3.12.
- **Impact:** `LegacyAPIWarning`/`DeprecationWarning` e quebra em upgrades futuros.
- **Recommendation:** `db.session.get(Model, id)` e helper `utcnow()` baseado em `datetime.now(timezone.utc)` → Playbook P-12

### F-10 [MEDIUM] `except:` nu e tratamento de erros descentralizado (AP-16)
- **File:** `routes/task_routes.py:62, 137, 204, 236, routes/user_routes.py:130, 149, routes/report_routes.py:186, 207, 221, utils/helpers.py:46, 49, 88, routes/report_routes.py:196-197`
- **Description:** 12 `except:` nus engolem qualquer exceção (inclusive `KeyboardInterrupt`); cada rota faz seu próprio rollback/resposta; `update_category` acessa `data` sem checar `None`.
- **Impact:** Falhas reais escondidas, respostas de erro inconsistentes.
- **Recommendation:** Exceções de domínio + `register_error_handlers` central com rollback da sessão → Playbook P-05

### F-11 [MEDIUM] Validação de tipos ausente — entradas inválidas viram 500 (AP-14)
- **File:** `routes/task_routes.py:104, 113, 181-184, 260-264, routes/user_routes.py:102-103, 124-125, routes/report_routes.py:178-180, 196-202`
- **Description:** `priority` não tem tipo verificado (`"alta" < 1` → `TypeError` 500, confirmado no baseline); `int(priority)` na busca levanta `ValueError`; `title`/`name` sem verificação de tipo; `active` aceita qualquer valor; cor de categoria não validada.
- **Impact:** Erros 500 e dados inconsistentes.
- **Recommendation:** Validadores únicos por recurso com modo parcial (update) → Playbook P-16

### F-12 [MEDIUM] Responsabilidades no módulo errado e camadas mortas (AP-20)
- **File:** `routes/report_routes.py:157-223, services/notification_service.py:1-48, utils/helpers.py:9-108, models/task.py:38-60`
- **Description:** O CRUD de categorias está em `report_routes`; `NotificationService` nunca é usado; `process_task_data`, `is_valid_color`, `log_action` e demais helpers não têm chamadas; `Task.validate_status/validate_priority/is_overdue` não são usados pelas rotas.
- **Impact:** A estrutura de pastas sugere uma arquitetura que o código não segue; difícil saber onde está cada regra.
- **Recommendation:** `routes/category_routes.py` + controller próprio; remover código morto ou passar a usá-lo pelos services → Playbook P-03

### F-13 [MEDIUM] Exclusão de categoria deixa tasks órfãs (AP-19)
- **File:** `routes/report_routes.py:211-223`
- **Description:** `DELETE /categories/<id>` remove a categoria sem tratar `tasks.category_id`, que passa a apontar para um registro inexistente.
- **Impact:** Tasks com `category_id` inválido em listagens e relatórios.
- **Recommendation:** Desassociar (`category_id = NULL`) as tasks na mesma transação → Playbook P-09

### F-14 [LOW] `print` usado como logging (AP-23)
- **File:** `routes/task_routes.py:149, 153, 219, 234, routes/user_routes.py:83, 89, 147, services/notification_service.py:21, 24, utils/helpers.py:39, 41`
- **Description:** Eventos e erros escritos com `print`.
- **Impact:** Sem níveis nem destino configurável.
- **Recommendation:** `logging.getLogger(__name__)` → Playbook P-15

### F-15 [LOW] Imports e dependências não usados (AP-24)
- **File:** `app.py:7, routes/task_routes.py:7, routes/user_routes.py:6, routes/report_routes.py:7-8, utils/helpers.py:3-7, models/task.py:3, requirements.txt:4-6`
- **Description:** `os, sys, json, time, hashlib, math, format_date, calculate_percentage` importados sem uso; `marshmallow` e `requests` no requirements sem nenhum import.
- **Impact:** Ruído e superfície de dependências desnecessária.
- **Recommendation:** Remover durante a refatoração.

### F-16 [LOW] Magic numbers/strings (AP-21)
- **File:** `routes/task_routes.py:96-114, 167-184, routes/user_routes.py:64, 71, 115, 120, routes/report_routes.py:24-28, 129-130, utils/helpers.py:110-116`
- **Description:** Limites 3/200 de título, prioridade 1–5 e default 3, senha mínima 4, roles e status literais, mapeamento prioridade→rótulo; `helpers.py` define constantes que ninguém usa.
- **Impact:** Regras de domínio espalhadas e duplicadas.
- **Recommendation:** `config/constants.py` como fonte única → Playbook P-13

### F-17 [LOW] Condicionais verbosas e aninhadas (AP-25)
- **File:** `models/task.py:38-60, models/user.py:34-38, routes/task_routes.py:30-57`
- **Description:** `if cond: return True else: return False` e 3 níveis de `if` para calcular uma expressão booleana.
- **Impact:** Legibilidade.
- **Recommendation:** Retornar a expressão diretamente (`return self.role == 'admin'`).

## Deprecated APIs

| File:Line | Deprecated API | Modern replacement |
|---|---|---|
| `routes/*.py` (16 ocorrências, ver F-09) | `Model.query.get(id)` (SQLAlchemy 2.x legacy) | `db.session.get(Model, id)` |
| `models/*.py`, `routes/*.py`, `utils/helpers.py`, `services/notification_service.py`, `seed.py` (ver F-09) | `datetime.utcnow()` (deprecated no Python 3.12) | `datetime.now(timezone.utc)` |

## Proposed target structure

```
task-manager-api/
├── app.py                     # entry point + create_app() (mesmo comando: python app.py)
├── seed.py                    # usa create_app()
├── .env.example
├── config/{settings.py, constants.py}
├── database.py
├── models/{task.py, user.py, category.py}        # mantidos; regras intrínsecas + utcnow
├── services/{task_service, user_service, auth_service, category_service, report_service}.py
├── controllers/{task, user, category, report}_controller.py + validators.py
├── routes/{task, user, category, report, system}_routes.py   # views finas (blueprints)
├── views/serializers.py       # whitelist de campos
├── middlewares/error_handler.py
└── tests/smoke.json
```

```
================================
Total: 17 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
