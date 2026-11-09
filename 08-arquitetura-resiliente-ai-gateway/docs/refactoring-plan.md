# Plano de refatoração: da v1 acoplada à aplicação atrás do AI Gateway

Este plano conduz `app/helpdesk/` da tag `v1-coupled` até a tag `v2-decoupled` (estrutura nova, mesmo comportamento) e registra o que mudou depois, na `main`. Os juízes de cada passo são dois instrumentos determinísticos:

- a suíte de caracterização (`tests/characterization/`, 17 testes, comando na seção "Como rodar" do README);
- a métrica de acoplamento (`python3 metrics/coupling.py <app/helpdesk> <nome>`, régua do requisito 3).

## 1. Ponto de partida medido (`v1-coupled`)

`metrics/results/v1-coupled.csv`:

| Componente | Ca | Ce | I | A | D | Leitura |
|---|---|---|---|---|---|---|
| `config` | 6 | 0 | 0,00 | 0 | 1,00 | zona de dor: chaves de provider, base URLs e nomes de modelo físico, importado por todo mundo |
| `llm` | 4 | 1 | 0,20 | 0 | 0,80 | zona de dor: dois SDKs concretos, um cliente por provider, usado por todas as features |
| `schemas` | 5 | 0 | 0,00 | 0 | 1,00 | zona de dor pela fórmula; tipos de valor (ver ADR 0009) |
| `classification`, `extraction`, `suggestion` | 1 | 3 | 0,75 | 0 | 0,25 | dependem de `config` e `llm` (concretos e voláteis) |
| `report` | 1 | 4 | 0,80 | 0 | 0,20 | depende de `config`, `llm`, `tickets` |
| `tickets` | 1 | 1 | 0,50 | 0 | 0,50 | lê o caminho do arquivo direto de `config` |
| `main` | 0 | 5 | 1,00 | 0 | 0,00 | só rotas |

O problema não é um número isolado: é a direção das dependências. Toda feature aponta para dois componentes concretos (`config`, `llm`) que concentram exatamente o que é volátil (provider, modelo, chave, política de chamada). Qualquer troca de modelo passa por eles e pede deploy.

## 2. Componentes-alvo e estratégia de cada um

| Alvo | Estratégia | Resultado esperado |
|---|---|---|
| `llm` | Inverter a dependência: criar a porta `TextModel` (`typing.Protocol`, em `ports.py`) com o que as features precisam ("gere texto para a capacidade X"); o acesso concreto vira um adaptador (`adapters/gateway.py`) que fala com o gateway. `llm.py` deixa de existir. | Features dependem de uma abstração (A = 1); o único componente concreto com cliente HTTP do gateway tem Ca 1 (só `main`). |
| `config` | Reduzir Ca: as features deixam de ler configuração; os valores (URL do gateway, chaves virtuais, timeouts, tamanho do lote) são injetados pelo ponto de composição. Nomes de modelo físico e chaves de provider saem da aplicação (vão para `gateway/config.yaml`). | `config` com Ca 1 (só `main`) e sem nada volátil de provider. |
| `classification`, `extraction`, `suggestion`, `report` | Compor em vez de herdar: cada feature recebe a porta por parâmetro e conhece só o nome da própria capacidade lógica. Nenhuma classe base de "feature" (herança não traria nada além de acoplamento). | Ce apenas em `ports` e `schemas`. |
| `tickets` | Inverter a dependência: porta `TicketSource` e adaptador `JsonlTicketSource`, que recebe o caminho do arquivo no construtor (em vez de importar `config`). | `report` depende da porta, não do arquivo. |
| `main` | Virar o ponto de composição: monta `GatewayTextModel` e `JsonlTicketSource` a partir de `config` e entrega às features. | I = 1 (o único lugar que conhece os concretos). |

## 3. Critério de pronto

Critério original (antes do piloto):

1. Suíte de caracterização 17/17 verde, sem nenhuma alteração em `tests/characterization/`.
2. Nenhum nome de modelo físico nem chave de provider em `app/` (`grep -rE "gpt-fake|claude-fake|FAKE_|sk-fake|sk-ant" app/` vazio).
3. D de cada componente-alvo menor que na v1.

Critério revisado (depois do piloto, ver seção 5), que vale para a `v2-decoupled` e para a `main`:

1. Suíte de caracterização 17/17 verde, sem alteração (na `v2-decoupled`).
2. `grep` de modelos físicos e chaves de provider em `app/` vazio.
3. Nenhum componente na zona de dor (A < 0,5, I < 0,5 e D ≥ 0,5), exceto os estáveis por natureza declarados no ADR 0009. O adaptador do gateway e as features nunca podem ser exceção.
4. Direção das dependências: as features importam só `ports`, `schemas` (e, na `main`, `errors`); só `main` importa `adapters.gateway` e `config`.

## 4. Piloto: F1 (`classification`) atrás da porta `TextModel`

Escopo do piloto: um único componente. Criados `ports.py` (só `TextModel.complete`) e `adapters/gateway.py` (`GatewayTextModel`, SDK `openai` apontado para `http://gateway:4000/v1` com a chave virtual); `classification.classify` passou a receber o modelo por parâmetro e a pedir a capacidade lógica `ticket-classification`; `main` monta o adaptador. As outras três features continuaram usando `llm.py`. O gateway subiu com a capacidade `ticket-classification` apontando para `openai/gpt-fake-large` (o mesmo modelo da v1).

Medição antes (v1) e depois do piloto:

| Componente | Antes (Ca, Ce, I, A, D) | Depois do piloto |
|---|---|---|
| `classification` | 1, 3, 0,75, 0, 0,25 | 1, 2, 0,67, 0, **0,33** |
| `llm` | 4, 1, 0,20, 0, 0,80 (dor) | 3, 1, 0,25, 0, 0,75 (dor) |
| `config` | 6, 0, 0,00, 0, 1,00 (dor) | 6, 0, 0,00, 0, 1,00 (dor) |
| `ports` | — | 2, 0, 0,00, 1, 0,00 |
| `adapters.gateway` | — | 1, 1, 0,50, 0, 0,50 |
| `main` | 0, 5, 1,00, 0, 0,00 | 0, 7, 1,00, 0, 0,00 |

Suíte de caracterização: 17/17 verde (a F1 já passando pelo gateway; `/admin/calls` mostrou `gpt-fake-large classify 200` para cada chamada).

## 5. Revisões do plano

### Revisão 1 (depois do piloto): o critério "D menor" estava errado

O piloto fez o D da `classification` **subir** de 0,25 para 0,33, mesmo com a estrutura claramente melhor: ela passou a importar menos coisas (Ce 3 → 2), o que baixa I e, com A = 0, afasta o ponto da Main Sequence. Perseguir "D menor" levaria a decisões ruins (manter imports desnecessários, ou criar classes abstratas só para mexer em A), exatamente o que as dicas do desafio chamam de desenhar o código em função da fórmula.

Mudança: o critério de pronto passou a ser zona de dor + direção das dependências (seção 3, critério revisado). A leitura completa está no ADR 0009.

### Revisão 2 (depois do piloto): `config` não sai da zona sozinho

O piloto também mostrou que `config` continuou com Ca 6: além das features, `llm` e `tickets` o importam, e `main` passou a importá-lo também. Tornar `config` "abstrato" não faz sentido (são valores). A estratégia para ele mudou de "tirar da zona" para "mudar de papel": nada de provider, modelo ou chave nele, e Ca 1 (só `main`). Para isso, `tickets` entrou no escopo da refatoração (porta `TicketSource` + adaptador `JsonlTicketSource` que recebe o caminho no construtor), o que não estava no plano original. Com Ca 1 e conteúdo só de ambiente, `config` é declarado estável por natureza no ADR 0009.

### Revisão 3 (ao fechar a `v2-decoupled`): o modo de resposta fica para depois da tag

Uma versão intermediária do código já trazia a F2 em streaming e a F3 assíncrona (o requisito 6). Rodada contra a suíte de caracterização da `v1-coupled`, ela falhou nos testes de F2 e F3: o corpo da resposta mudou (SSE em vez de JSON; `202` em vez de `200`). Pelo critério de pronto isso é reescrita, não refatoração. A `v2-decoupled` foi fechada com as quatro features síncronas como na v1 (o mesmo `TextModel.complete`, a F3 em série), e o streaming, o assíncrono e o `errors.py` com erros de domínio entraram só na `main`, com os testes de F2 e F3 atualizados para o contrato novo (permitido pelo requisito 2).

### Revisão 4 (na `main`): erros de domínio fora do HTTP

Na `v2-decoupled` as features ainda lançam `fastapi.HTTPException` (dependência externa, invisível para a métrica, mas que mistura regra de negócio com HTTP). Na `main`, com o gateway devolvendo recusas de orçamento/limite e falhas de toda a cadeia de fallback, o mapeamento de falhas cresceu. Foi criado `errors.py` (exceções do domínio, sem lógica) e o status HTTP de cada erro passou a ser decidido num único handler em `main`. `errors` tem Ca 6 e cai na zona de dor pela fórmula; está declarado estável por natureza no ADR 0009.

## 6. Escala da refatoração e medições

| Medição | Zona de dor | Observação |
|---|---|---|
| `v1-coupled` | `config`, `llm`, `schemas` | features dependem de concretos voláteis |
| piloto | `config`, `llm`, `schemas` | só a F1 atrás da porta |
| `v2-decoupled` | `config` (Ca 1, só ambiente), `schemas` | `llm` removido; features com Ce só em `ports` e `schemas`; `adapters.gateway` Ca 1 |
| `main` | `config`, `errors`, `schemas` (os três declarados no ADR 0009) | `jobs` (F3 assíncrona) e `errors` novos; adaptador com `stream` |

Os CSVs e gráficos estão em `metrics/results/`. O script é o mesmo nas três medições; a `v1-coupled` e a `v2-decoupled` foram medidas rodando o script desta branch sobre um checkout de cada tag.

## 7. Handoff para o agente de IA

Agente: Claude Code (modelo Claude), trabalhando direto no repositório, com acesso a terminal e Docker.

O que foi entregue ao agente:

- este plano (alvos, estratégia por componente e critério de pronto revisado);
- o comando da suíte de caracterização e a regra "nenhum arquivo de `tests/characterization/` pode mudar até a tag `v2-decoupled`";
- o comando da métrica e a regra de aceite: nenhum componente novo na zona de dor fora da lista do ADR 0009, e features sem import de `config` nem de `adapters`;
- as restrições do desafio: `provider-fake/`, `edge/` e `data/` intocados; nenhum nome de modelo físico nem chave de provider em `app/`; um `large` por trás de cada capacidade na `v2-decoupled`;
- a ordem de execução: piloto na F1, medir, revisar o plano, depois `extraction`, `suggestion`, `report`/`tickets`, e por último remover `llm.py` e limpar `config`.

Como cada entrega do agente foi aceita ou rejeitada:

1. A cada componente migrado: `docker compose up -d --build --wait`, suíte de caracterização e métrica. Só seguia para o próximo componente com 17/17 verde e sem regressão na direção das dependências.
2. `/admin/calls` conferido depois de cada etapa: toda chamada da suíte chegando ao provider pelo gateway, sempre no modelo `large` do provider da v1.
3. Critério que descarta o caminho de menor diff: manter `llm.py` como fachada e só apontar as base URLs para o gateway faria a suíte passar, mas deixaria `llm` com Ca 4 e D 0,80 na zona de dor e as features dependentes de um concreto (opção 1 do ADR 0008). Pela regra de aceite, não fecha a tag.
4. Rejeitado: fechar a `v2-decoupled` com a F2 em streaming e a F3 assíncrona (revisão 3). A suíte de caracterização falhou nos testes de F2 e F3, então o código da tag voltou ao modo síncrono.
5. Regra para resiliência: retry só no gateway. O SDK `openai` faz 2 retries por padrão; somados ao retry do gateway, o `/admin/calls` mostraria as tentativas multiplicadas. O adaptador usa `max_retries=0` e a política inteira fica no gateway (ADR 0005).

Resultado: `v2-decoupled` com 17/17 na mesma suíte da `v1-coupled` (`git diff v1-coupled v2-decoupled -- tests/characterization/` vazio) e medição em `metrics/results/v2-decoupled.csv`.
