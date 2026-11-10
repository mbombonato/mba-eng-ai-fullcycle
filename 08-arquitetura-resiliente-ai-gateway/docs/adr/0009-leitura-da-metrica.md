# 0009. Leitura da métrica de acoplamento e componentes estáveis por natureza

- Status: aceita
- Data: 2026-11-09
- Nível: software

## Contexto

A régua é fixa (requisito 3): componente é cada `.py` de `app/helpdesk/` (exceto `__init__.py`), dependência é import que resolve para outro componente, A conta classes que herdam de `Protocol` ou `ABC`. O script é `metrics/coupling.py` e as medições estão em `metrics/results/`.

A fórmula põe na zona de dor (A < 0,5, I < 0,5, D ≥ 0,5) qualquer componente concreto muito usado e que não depende de ninguém, inclusive os que quase nunca mudam. É preciso separar "concreto e estável porque é só um tipo" de "concreto e estável porque todo mundo depende de uma decisão volátil".

## Opções consideradas

1. Perseguir D baixo em todos os componentes (ex.: transformar tipos de valor em protocolos, ou criar imports artificiais).
2. Declarar como estáveis por natureza os componentes que são só tipos/valores, com justificativa, e exigir que os demais saiam da zona de dor.

## Decisão

Opção 2. Critério de leitura:

- Fora da zona de dor obrigatoriamente: o componente que chama o gateway (`adapters.gateway`) e as features (`classification`, `suggestion`, `extraction`, `report`), além de `jobs`, `tickets`, `ports` e `main`.
- Estáveis por natureza (podem ficar na zona de dor):
  - `schemas`: modelos pydantic do contrato HTTP (`TicketInput`, `Classification`, ...). São tipos de valor; mudam só quando o contrato público muda, o que já é uma mudança coordenada com os consumidores. Não dependem de nada e não têm comportamento.
  - `errors`: as cinco exceções do domínio, sem lógica. Mudam quando surge um novo tipo de falha de negócio, o que é raro e aditivo.
  - `config`: na `main`, só lê variáveis de ambiente (URL do gateway, as duas chaves virtuais, timeouts, tamanho de lote). Não contém provider, modelo, chave de provider nem regra; quem o importa é só o ponto de composição (Ca = 1). O que muda na operação muda por variável de ambiente, não por edição do módulo. Na v1 ele era o oposto (nomes de modelo físicos e chaves, Ca = 6) e saiu da lista de problemas por ter mudado de papel, não por exceção.

Leitura das três medições (detalhe no README, seção Métrica):

| Componente | v1-coupled (I, A, D) | v2-decoupled | main |
|---|---|---|---|
| `llm` | 0,20 / 0 / 0,80 (dor) | removido | removido |
| `config` | 0,00 / 0 / 1,00 (dor, Ca 6) | 0,00 / 0 / 1,00 (Ca 1) | 0,00 / 0 / 1,00 (Ca 1, exceção declarada) |
| `ports` | — | 0,00 / 1 / 0,00 | 0,00 / 1 / 0,00 |
| `adapters.gateway` | — | 0,50 / 0 / 0,50 | 0,67 / 0 / 0,33 |
| features | 0,75–0,80 / 0 / 0,20–0,25 | 0,67 / 0 / 0,33 | 0,67–0,75 / 0 / 0,25–0,33 |

O D das features subiu levemente da v1 para a v2 (0,20-0,25 → 0,33) porque elas passaram a importar menos coisas (Ce 3 → 2): o número piorou porque a instabilidade caiu, mas o que elas importam agora é uma porta abstrata e tipos estáveis, em vez de `config` e `llm`. A métrica aponta onde olhar; o critério de pronto é a zona de dor e a direção das dependências, não o menor D possível.

## Consequências

- Uma mudança que coloque nomes de modelo ou regras em `config`, ou faça uma feature importar `config` ou o adaptador, invalida a exceção e precisa revisar esta ADR.
- `tickets` fica no limite (I = 0,50, D = 0,50; fora da zona porque I não é < 0,5); se outro componente além de `main` passar a importá-lo, ele entra na zona e deve virar dependência pela porta `TicketSource`.

## Evidência

`python3 metrics/coupling.py app/helpdesk main` lista como zona de dor só `config`, `errors` e `schemas`.
