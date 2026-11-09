# Análise de Projeto — Heurísticas (Fase 1)

Objetivo: descrever o projeto com fatos verificáveis (manifestos, imports, DDL), nunca por suposição.

## 1. Inventário de arquivos

```bash
# arquivos-fonte (ajuste as extensões à stack)
find . -type f \( -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.go' -o -name '*.java' -o -name '*.rb' -o -name '*.php' \) \
  -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/venv/*' \
  -not -path '*/.git/*' -not -path '*/.claude/*' -not -path '*/__pycache__/*' -not -path '*/dist/*' -not -path '*/build/*' \
  | sort | xargs wc -l
```

- Conte **apenas código da aplicação** (inclua seeds/scripts que rodam com a aplicação; exclua testes,
  lockfiles, bancos `.db`, arquivos gerados).
- Arquivos `__init__.py` vazios contam como arquivo, mas não influenciam a classificação.

## 2. Linguagem e framework

| Evidência (manifesto / import) | Linguagem | Framework |
|---|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `*.py` | Python | `flask` → Flask · `fastapi` → FastAPI · `django` → Django |
| `package.json` + `*.js`/`*.ts` | JavaScript/TypeScript (Node.js) | `express` → Express · `@nestjs/core` → NestJS · `koa` → Koa · `fastify` → Fastify |
| `go.mod` | Go | `gin-gonic/gin` → Gin · `labstack/echo` → Echo · `net/http` puro |
| `pom.xml` / `build.gradle` | Java/Kotlin | `spring-boot-starter-web` → Spring Boot |
| `Gemfile` | Ruby | `rails` → Rails · `sinatra` → Sinatra |
| `composer.json` | PHP | `laravel/framework` → Laravel · `slim/slim` → Slim |

- A **versão** vem do manifesto (`flask==3.1.1`, `"express": "^4.18.2"`). Se houver lockfile
  (`package-lock.json`, `poetry.lock`), reporte a versão resolvida quando disponível.
- Confirme o framework pelo import real (`from flask import`, `require('express')`), não só pelo manifesto.
- Versão da linguagem: `.python-version`, `engines` do `package.json`, `runtime.txt`, Dockerfile;
  se ausente, informe "não fixada".

## 3. Banco de dados

| Sinal | Banco / acesso |
|---|---|
| `import sqlite3`, `sqlite3.connect(` | SQLite via driver nativo (SQL manual) |
| `flask_sqlalchemy`, `SQLAlchemy(`, `db.Model` | ORM SQLAlchemy (ver `SQLALCHEMY_DATABASE_URI`) |
| `require('sqlite3')`, `new sqlite3.Database(` | SQLite (Node, API de callbacks) |
| `':memory:'` | banco em memória — dados somem a cada boot |
| `pg`, `psycopg`, `mysql2`, `pymysql` | PostgreSQL / MySQL com SQL manual |
| `sequelize`, `prisma`, `typeorm`, `mongoose` | ORMs/ODMs Node |

**Tabelas/entidades**: `grep -n "CREATE TABLE" -r .`, `grep -n "__tablename__" -r .`,
classes que herdam de `db.Model`/`Base`, arquivos de migration, schemas do Prisma.

## 4. Entry point, boot e rotas

- Entry point: arquivo com `app.run(`, `app.listen(`, `if __name__ == "__main__"`, `"main"`/`"scripts.start"` do `package.json`.
- Porta: argumento de `run/listen`, variável `PORT`, config.
- Pré-requisitos de boot: seeds (`seed.py`), migrations, variáveis de ambiente.
- **Inventário de rotas** (obrigatório, usado na validação):

| Stack | Como achar |
|---|---|
| Flask | `@app.route`, `@<bp>.route`, `add_url_rule(`, `register_blueprint(` (verifique `url_prefix`) |
| FastAPI | `@app.get/post/...`, `APIRouter`, `include_router(prefix=)` |
| Express | `app.get/post/put/delete/patch(`, `router.<verbo>(`, `app.use('/prefixo', router)` |
| NestJS | `@Controller('x')` + `@Get()`/`@Post()` |
| Django | `urls.py` (`path(`, `re_path(`) |

## 5. Domínio

Inferir pelo vocabulário dominante de rotas, tabelas e campos:

- `produtos`, `pedidos`, `itens_pedido`, `carrinho`, `checkout` → **E-commerce**
- `courses`, `enrollments`, `lessons`, `students` → **LMS / plataforma de cursos** (com checkout se houver `payments`)
- `tasks`, `projects`, `categories`, `due_date`, `priority` → **Task Manager**
- `accounts`, `transactions`, `balance` → **Financeiro/bancário**

Descreva: domínio + entidades principais (ex.: "E-commerce API (produtos, pedidos, usuários)").

## 6. Classificação da arquitetura atual

| Classificação | Sinais |
|---|---|
| **Monolito sem camadas** | Poucos arquivos concentrando rotas + SQL + regras; uma classe/arquivo "faz tudo" (ex.: `AppManager`, `models.py` com SQL e regras de 4 domínios); sem pastas por responsabilidade |
| **Camadas parciais** | Existem pastas `models/`, `routes/`, `services/`, `utils/`, mas rotas ainda contêm regra de negócio/consultas, services subutilizados, config hardcoded no entry point |
| **MVC / camadas completas** | Config isolada, models só com dados, controllers orquestram, rotas finas, error handler central, DI no composition root |
| **Outra** | Clean/Hexagonal, serverless etc. — descreva e audite contra as mesmas regras de responsabilidade |

Registre também **acoplamentos marcantes** (ex.: "classe instancia o banco no construtor",
"rotas importam o ORM diretamente") — eles alimentam a Fase 2.

## 7. Checklist de saída da Fase 1

- [ ] Linguagem e framework confirmados por manifesto **e** import
- [ ] Número de arquivos/linhas obtido por comando, não estimado
- [ ] Banco e tabelas listados
- [ ] Comando de boot e porta identificados
- [ ] Inventário de rotas completo (método, caminho, handler, arquivo:linha)
- [ ] Domínio e arquitetura classificados com justificativa
