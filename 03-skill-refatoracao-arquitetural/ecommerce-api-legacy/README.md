# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch` —
**já refatorada para MVC** pela skill (relatório em `../reports/audit-project-2.md`).

## Como rodar

```bash
npm install
cp .env.example .env   # defina ADMIN_TOKEN (e PAYMENT_GATEWAY_KEY, se houver)
npm start
```

A aplicação sobe em `http://localhost:3000` (`PORT`). O banco SQLite é em memória por padrão
(`DATABASE_FILE=:memory:`) e carrega seeds automaticamente no boot. Exemplos em `api.http`.

## Estrutura

```
src/
├── server.js               # entry point (npm start)
├── app.js                  # composition root: createApp({ db, config, logger })
├── config/                 # index.js (ambiente) e constants.js (regras/status)
├── database/               # wrapper promisificado + transações, schema e seed
├── models/                 # user, course, enrollment, payment, auditLog (SQL parametrizado)
├── services/               # checkout, gateway de pagamento, relatório, usuários, hash de senha
├── controllers/            # checkout, report, user (fluxo + validação de entrada)
├── views/routes.js         # rotas /api/*
├── middlewares/            # errorHandler, requireAdmin, asyncHandler
└── utils/                  # errors (exceções de domínio) e logger
tests/smoke.json            # smoke test de todos os endpoints
```

## Mudanças intencionais de contrato (segurança)

- `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem `X-Admin-Token` igual a `ADMIN_TOKEN` (403 caso contrário; sem token configurado ficam desabilitadas).
- Novos usuários precisam enviar `pwd` (antes recebiam a senha default `123456`); senhas são gravadas com scrypt + salt.
- Erros são JSON `{"error": "..."}` (antes texto puro) — status HTTP preservados.
- `DELETE /api/users/:id` remove matrículas/pagamentos do usuário na mesma transação, devolve JSON e responde 404 para usuário inexistente.

## Validação

```bash
ADMIN_TOKEN=smoke PORT=3100 npm start &
ADMIN_TOKEN=smoke python3 .claude/skills/refactor-arch/scripts/smoke_test.py tests/smoke.json --base-url http://127.0.0.1:3100
```
