# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch` — **já refatorada
para MVC** pela skill (relatório em `../reports/audit-project-3.md`). O projeto já tinha
`models/`, `routes/`, `services/` e `utils/`; a refatoração manteve essas pastas com papéis
corretos e acrescentou `config/`, `controllers/`, `views/` e `middlewares/`.

## Como rodar

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env      # defina SECRET_KEY
.venv/bin/python seed.py
.venv/bin/python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` (`HOST`/`PORT`). O `seed.py` popula o banco SQLite
(`DATABASE_URL`, padrão `sqlite:///tasks.db` → `instance/tasks.db`) com usuários, categorias e tasks
de exemplo — **rode-o antes do primeiro boot**.

## Estrutura

```
app.py                      # entry point + create_app() (composition root)
seed.py                     # dados de exemplo
config/                     # settings.py (ambiente/.env) e constants.py (regras de domínio)
database.py                 # extensão Flask-SQLAlchemy
models/                     # Task, User, Category (+ regras intrínsecas: is_overdue, hash de senha)
services/                   # task, user, category, auth (token assinado), report (agregações)
controllers/                # fluxo de cada caso de uso + validators.py
routes/                     # blueprints finos (views de roteamento): tasks, users, categories, reports, system
views/serializers.py        # whitelist de campos das respostas
middlewares/error_handler.py
utils/clock.py              # utcnow() sem API deprecated
tests/smoke.json            # smoke test de todos os endpoints
```

## Mudanças intencionais de contrato (segurança)

- Respostas de usuário (`GET/POST/PUT /users`, `POST /login`) não incluem mais o hash `password`.
- Senhas usam scrypt com salt; hashes MD5 antigos são migrados automaticamente no primeiro login válido.
- Senha mínima para novos usuários/alterações: 8 caracteres (antes 4).
- `POST /login` devolve um token **assinado** com `SECRET_KEY` (expiração `TOKEN_MAX_AGE_SECONDS`) em vez de `fake-jwt-token-<id>`.
- Entradas com tipo inválido (ex.: `priority: "alta"`) retornam 400 em vez de 500; excluir categoria desassocia as tasks.

## Validação

```bash
DATABASE_URL=sqlite:////tmp/smoke.db .venv/bin/python seed.py
DATABASE_URL=sqlite:////tmp/smoke.db PORT=5113 .venv/bin/python app.py &
python3 .claude/skills/refactor-arch/scripts/smoke_test.py tests/smoke.json --base-url http://127.0.0.1:5113
```
