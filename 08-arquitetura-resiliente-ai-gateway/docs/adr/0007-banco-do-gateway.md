# 0007. Adicionar o serviço gateway-db (Postgres) e provisionar as chaves no boot do gateway

- Status: aceita
- Data: 2026-11-09
- Nível: software

## Contexto

O requisito 5 pede chaves virtuais com orçamento e com limite de requisições (ADR 0006). No LiteLLM Proxy, chaves virtuais, gasto acumulado e orçamento vivem num banco Postgres; sem banco, só existe a master key, sem orçamento por chave. Além disso, as chaves precisam existir sem passo manual: `cp .env.example .env && docker compose up -d --build --wait` tem que deixar tudo pronto.

## Opções consideradas

1. Implementar orçamento e limite na aplicação, sem banco.
2. Postgres dedicado ao gateway (`gateway-db`) e um serviço extra de inicialização que cria as chaves.
3. Postgres dedicado ao gateway e provisionamento das chaves dentro do próprio container do gateway.

## Decisão

Opção 3.

- `gateway-db`: `postgres:16-alpine`, usado só pelo gateway, sem porta publicada no host. Existe por causa do requisito 5 (governança); nenhum outro serviço o acessa.
- `gateway/entrypoint.sh` sobe o LiteLLM e roda `gateway/provision_keys.py`, que cria ou atualiza (idempotente) as chaves de `gateway/keys.json` com os valores vindos das variáveis de ambiente. O healthcheck do gateway só passa depois disso, e o `app` depende do gateway saudável: a aplicação nunca sobe sem as chaves.
- A opção 1 traria a governança de volta para a aplicação, contra o ADR 0002. A opção 2 acrescentaria mais um serviço ao compose só para rodar um script uma vez.

## Consequências

- Mais um serviço para operar (backup do banco, se o gasto acumulado importar).
- O banco usa o volume anônimo da imagem do Postgres: `docker compose down -v` zera gasto e chaves, que são recriadas no próximo `up`.
- O primeiro `up` leva ~40 s a mais (migrações do LiteLLM).

## Evidência

- `docker compose logs gateway | grep chave` mostra `chave helpdesk-realtime criada` (ou `atualizada`).
- `curl -s "localhost:4000/key/info?key=sk-helpdesk-reports-0001" -H "Authorization: Bearer $LITELLM_MASTER_KEY"` devolve orçamento, limite e gasto.
