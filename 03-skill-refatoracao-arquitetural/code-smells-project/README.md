# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch` — **já refatorada
para MVC** pela skill (relatório em `../reports/audit-project-1.md`).

## Como rodar

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
export ADMIN_TOKEN=troque-este-token SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(32))")
.venv/bin/python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` (ajuste com `HOST`/`PORT`). O banco SQLite
(`DATABASE_PATH`, padrão `loja.db`) é criado no boot, já com produtos e usuários de exemplo
(senhas gravadas com hash). Variáveis disponíveis em `.env.example`.

## Estrutura

```
app.py                      # entry point (python app.py / flask --app app run)
src/
├── app.py                  # composition root: create_app()
├── config/                 # settings.py (ambiente) e constants.py (regras de domínio)
├── database/               # conexão por requisição, schema e seed
├── models/                 # produto, usuário e pedido (SQL parametrizado)
├── services/               # pedido, relatório de vendas, notificações
├── controllers/            # fluxo de cada caso de uso + validators
├── views/                  # routes.py (rotas) e serializers.py (whitelist de campos)
└── middlewares/            # error_handler.py e auth.py (X-Admin-Token)
tests/smoke.json            # smoke test de todos os endpoints
```

## Mudanças intencionais de contrato (segurança)

- `POST /admin/query` (execução de SQL arbitrário) foi **removido**.
- `POST /admin/reset-db` exige o header `X-Admin-Token` igual a `ADMIN_TOKEN` (sem token configurado a rota fica desabilitada).
- Respostas de usuários não incluem mais `senha`; `/health` não expõe `secret_key`, `db_path`, `debug` nem `ambiente`.
- Entradas inválidas que antes geravam 500 agora retornam 400/404/409.

## Validação

```bash
ADMIN_TOKEN=smoke DATABASE_PATH=/tmp/smoke.db PORT=5111 .venv/bin/python app.py &
python3 .claude/skills/refactor-arch/scripts/smoke_test.py tests/smoke.json --base-url http://127.0.0.1:5111
```
(com `ADMIN_TOKEN=smoke` exportado também no shell do smoke test)
