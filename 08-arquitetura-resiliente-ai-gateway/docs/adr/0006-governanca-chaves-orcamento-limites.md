# 0006. Uma chave virtual por perfil de carga, com orçamento e limite de requisições

- Status: aceita
- Data: 2026-11-09
- Nível: solução

## Contexto

O ADR 0001 fixou um teto mensal de US$ 50 para a IA do helpdesk. Na v1 nada limita gasto nem volume: o relatório do mês gasta ≈ US$ 0,85 por pedido mesmo quando ninguém recebe o resultado, e a aplicação usa as chaves dos providers. O requisito pede pelo menos uma chave com orçamento e uma com limite de requisições, com a recusa acontecendo antes de chegar ao provider.

As features têm perfis diferentes: F1, F2 e F4 são muitas chamadas pequenas e interativas; F3 são rajadas de 34 chamadas grandes (~6.600 tokens de entrada cada) por pedido.

## Opções consideradas

1. Uma chave única para a aplicação.
2. Uma chave por feature (quatro chaves).
3. Uma chave por perfil de carga: tempo real (F1, F2, F4) e relatórios (F3).

## Decisão

Opção 3, provisionada automaticamente no boot do gateway a partir de `gateway/keys.json`:

| Chave (alias) | Features | Capacidades permitidas | Orçamento | Limite |
|---|---|---|---|---|
| `helpdesk-realtime` | F1, F2, F4 | `ticket-classification`, `reply-suggestion`, `order-extraction` | US$ 30 / 30 dias | 120 req/min |
| `helpdesk-reports` | F3 | `topics-report` | US$ 20 / 30 dias | 120 req/min |

- A opção 1 deixaria uma rajada de relatórios consumir o orçamento e o limite das features em que alguém está esperando. A opção 2 multiplica chaves sem diferença de política entre F1, F2 e F4.
- Os orçamentos somam o teto do ADR 0001. O custo é calculado pelo gateway com os preços por token declarados em `gateway/config.yaml` (copiados da tabela do provider).
- Cada chave só chama as próprias capacidades: um bug na F3 não consegue gastar o orçamento do tempo real e vice-versa.
- A aplicação recebe só os valores das duas chaves virtuais (variáveis `GATEWAY_REALTIME_KEY` e `GATEWAY_REPORTS_KEY`). A master key do gateway e as chaves dos providers não chegam ao serviço `app`.
- Recusa por limite ou orçamento chega à aplicação como `429` do gateway e vira `429` explícito na F1, F2 e F4 (`{"detail": "... limite de requisições esgotado"}`) e `failed` com motivo na F3.

## Consequências

- Gasto e volume por perfil ficam visíveis no gateway (`/key/info`).
- O provisionamento reaplica os valores de `keys.json` a cada início do gateway: um ajuste manual feito pela API de administração é desfeito no próximo restart (útil para o roteiro de demonstração).
- Os limites são do gateway e não deduplicam pedidos: dois relatórios do mesmo período custam duas vezes (deduplicação fora de escopo).

## Evidência

O roteiro de governança do README (e `tests/acceptance/test_governance.py`): com `rpm_limit` reduzido para 1, a segunda F1 recebe `429` e o número de chamadas em `/admin/calls` não aumenta; com `max_budget` igual ao gasto atual, o pedido da F3 chega a `failed` com motivo "orçamento esgotado" e nenhuma chamada nova aparece em `/admin/calls`.
