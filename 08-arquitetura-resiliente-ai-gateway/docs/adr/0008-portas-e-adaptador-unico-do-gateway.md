# 0008. Features dependem de portas; um único adaptador fala com o gateway

- Status: aceita
- Data: 2026-11-09
- Nível: software

## Contexto

Na v1 (`metrics/results/v1-coupled.csv`), as quatro features importam `config` e `llm`, dois componentes concretos e voláteis: `llm` (Ca 4, I 0,20, A 0, D 0,80) e `config` (Ca 6, D 1,00) estão na zona de dor. Toda mudança de provider, modelo, credencial ou política de chamada passava por eles e se propagava para as features. As features também lançavam `HTTPException`, misturando regra de negócio com HTTP.

## Opções consideradas

1. Manter `llm.py` e só apontar as base URLs para o gateway.
2. Portas (`typing.Protocol`) para o que as features precisam (`TextModel`, `TicketSource`), um adaptador concreto por porta, e montagem no ponto de composição (`main.py`).
3. Herança de uma classe base abstrata de "feature".

## Decisão

Opção 2.

- `ports.py`: `TextModel` (`complete` e `stream` por capacidade lógica) e `TicketSource`. Só protocolos (A = 1).
- `adapters/gateway.py`: `GatewayTextModel`, o único componente de `app/` que usa um cliente do gateway (SDK `openai`). Traduz erros HTTP do gateway para os erros do domínio (`errors.py`). Só `main.py` o importa.
- `tickets.py`: `JsonlTicketSource`, adaptador da porta `TicketSource`.
- Features (`classification`, `suggestion`, `extraction`, `report`) recebem a porta por parâmetro e conhecem apenas a própria capacidade lógica, os tipos (`schemas`) e os erros do domínio (`errors`). Não importam `config` nem o adaptador.
- `errors.py`: erros do domínio; `main.py` decide o status HTTP de cada um num único handler.
- `config.py`: só leitura de ambiente, consumida só por `main.py`.
- `jobs.py`: o ciclo de vida das tarefas da F3 (ADR 0004).
- A opção 1 mantém `llm` como dependência concreta de todas as features (continua na zona de dor) e não separa a política de chamada do formato. A opção 3 acopla as features por herança sem ganho: composição com a porta injetada basta.

## Consequências

- Trocar o meio de acesso aos modelos (outro gateway, outro SDK) é escrever um novo adaptador de `TextModel` e mudar uma linha em `main.py`.
- As features podem ser testadas com um `TextModel` falso, sem rede.
- `main.py` concentra as dependências concretas (I = 1, como deve ser no ponto de composição).

## Evidência

- `grep -rn "from openai\|import openai" app/` só encontra `app/helpdesk/adapters/gateway.py`.
- `grep -rn "adapters" app/helpdesk --include=*.py` só encontra `main.py`.
- `metrics/results/main.csv`: `adapters.gateway` Ca 1 (só `main`), features com Ce apenas em `ports`, `schemas` e `errors`.
