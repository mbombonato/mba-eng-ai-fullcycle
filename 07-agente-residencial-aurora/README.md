# Assistente virtual do Residencial Aurora

Assistente de chat do condomínio construído com **Google ADK 2.9.1** e exposto por uma
API **FastAPI** em `http://localhost:8000`. O morador reserva e cancela áreas comuns,
autoriza visitantes e tira dúvidas sobre o regulamento. As regras críticas valem
**no código**, não no prompt: *o modelo decide o caminho, o código decide o que é
permitido.*

O enunciado completo está em [`ENUNCIADO.md`](ENUNCIADO.md).

```
src/aurora/
├── agents.py       # agente principal + 3 especialistas (ADK)
├── tools.py        # tools de reservas, visitantes e regulamento
├── db.py           # SQLite do condomínio (índice único, códigos, sessões)
├── regulamento.py  # divisão do regulamento em capítulos e busca de UM capítulo
├── service.py      # Runner, sessões persistidas, confirmações pendentes
├── api.py          # rotas HTTP (contrato do enunciado)
├── restore.py      # comando de restauração dos dados
└── config.py       # variáveis de ambiente
tests/              # 26 testes sem chave de API (LLM falso determinístico)
dados/              # estado inicial (intocado)
var/                # bancos SQLite gerados em tempo de execução (fora do Git)
```

---

## Arquitetura

```
                 POST /sessoes/{id}/mensagens            POST /sessoes/{id}/confirmacoes
                               │                                     │
                               ▼                                     ▼
                       AuroraService (service.py) ── Runner ADK ── DatabaseSessionService (var/sessoes.db)
                               │
                 ┌─────────────┴──────────────┐
                 ▼                            │
        assistente_aurora (principal)         │  tools / sub-agentes
        ├── sub-agente  especialista_reservas    → listar_areas, consultar_disponibilidade,
        │                                          listar_minhas_reservas, reservar_area,
        │                                          cancelar_minha_reserva
        ├── sub-agente  especialista_visitantes  → listar_meus_visitantes, autorizar_visitante
        └── AgentTool   especialista_regulamento → consultar_regulamento
                                                   │
                                     CondominioRepository (var/condominio.db)
```

| Agente | Responsabilidade | Como é acionado | Por quê |
|---|---|---|---|
| `assistente_aurora` | Conversa com o morador e distribui o trabalho. Não tem tools de dados e **não recebe o regulamento** nas instruções. | Raiz do `App` (`agents.py`, `build_root_agent`). | Ponto único de entrada; prompt curto e barato em todas as chamadas. |
| `especialista_reservas` | Reservar, consultar disponibilidade, listar e cancelar reservas do apartamento da sessão. | **Sub-agente por transferência** (`transfer_to_agent`). | A tool `reservar_area` pede confirmação. Para retomar a execução, a resposta da confirmação precisa chegar ao agente que fez o pedido; com sub-agentes o pedido fica nos eventos da **mesma sessão persistida**, e o Runner retoma no autor da chamada original. Num `AgentTool` o especialista roda numa sessão em memória descartável, fora da sessão persistida onde a rota de confirmações procura os pedidos pendentes; por isso optei por sub-agentes. |
| `especialista_visitantes` | Autorizar visitantes e listar os visitantes do apartamento da sessão. | **Sub-agente por transferência**. | Mesmo motivo: `autorizar_visitante` sempre pede confirmação. |
| `especialista_regulamento` | Responder dúvidas consultando **um** capítulo do regulamento. | **`AgentTool`** do agente principal. | O `AgentTool` executa o especialista numa sessão isolada (`InMemorySessionService`); só a resposta final volta para a sessão do morador. O capítulo consultado nunca entra no histórico, e por isso não acompanha as mensagens seguintes. |

Os especialistas de reservas e de visitantes usam `disallow_transfer_to_peers=True`:
quando o pedido sai do assunto deles, devolvem o controle ao principal. A topologia
fica previsível para o Runner na hora de retomar uma confirmação.

**Armazenamento:** SQLite, sem serviço externo.
- `var/condominio.db`: apartamentos, áreas, reservas (com status `ativa`/`cancelada`), visitantes, códigos emitidos e o vínculo sessão→apartamento. Nasce de `dados/` na primeira subida ou no comando de restauração.
- `var/sessoes.db`: sessões e eventos do ADK (`DatabaseSessionService` com `sqlite+aiosqlite`).

**Modelo:** Gemini via Google AI Studio. O padrão é `gemini-3.6-flash`.
O modelo pode ser trocado em `AURORA_MODELO`, ou por agente em `AURORA_MODELO_PRINCIPAL` e `AURORA_MODELO_ESPECIALISTAS`.

---

## Garantias

### Garantia 1: cobrança ou acesso só com confirmação

- **`src/aurora/tools.py`, `reservar_area` e `autorizar_visitante`:** quando a área tem taxa (`area_obj.gera_cobranca`) ou a ação é autorizar visitante, a tool só grava se `tool_context.tool_confirmation` existir com `confirmed=True`. Sem esse objeto, a tool chama `tool_context.request_confirmation(hint=..., payload={"area", "data", ...})` / `payload={"nome", "data"}` e retorna `aguardando_confirmacao` sem gravar nada. Se a confirmação for negada, retorna `recusada`. Área com taxa `0` (quadra) e cancelamento gravam direto, sem confirmação.
- **`src/aurora/service.py`, `confirmacoes_pendentes(session)`:** a lista de pendentes é calculada a partir dos **eventos persistidos**: chamadas `adk_request_confirmation` que ainda não têm `FunctionResponse`. `detalhes` vem do `payload` (`area`/`data` ou `nome`/`data`).
- **`src/aurora/service.py`, `responder_confirmacao`:** se o `id` não está entre as pendentes **desta sessão**, a função levanta `ConfirmacaoInexistente`, que vira `409` (`api.py`), antes de qualquer execução. Isso cobre id inventado, id de outra sessão e id já respondido. Se o id é válido, a resposta vai ao Runner como `FunctionResponse(name="adk_request_confirmation", id=..., response={"confirmed": ...})`, e o ADK reexecuta a tool original no agente que pediu a confirmação.
- **Uma única execução:** a reserva ou visita aprovada é gravada com `confirmacao_id` = id da chamada da tool, e a coluna é `UNIQUE` (`src/aurora/db.py`, tabelas `reservas` e `visitantes`). `criar_reserva`/`autorizar_visitante` devolvem `ja_executada` se esse id já foi gravado. `_ja_existe_pedido_pendente` (`tools.py`) evita abrir dois pedidos iguais na mesma sessão.

**Por que não depende do modelo:** `tool_context.tool_confirmation` só é preenchido pelo ADK a partir de uma `FunctionResponse` de `adk_request_confirmation`, e só a rota `/confirmacoes` cria essa resposta. A rota de mensagens envia apenas `Part(text=...)`. Escrever "já estou confirmando" no chat não preenche o objeto, e o pedido continua pendente.

### Garantia 2: cada sessão pertence a um apartamento

- **`src/aurora/service.py`, `criar_sessao`:** o apartamento é gravado uma única vez, em `state={"apartamento": ...}`, e registrado na tabela `sessoes` de `condominio.db` (`repo.registrar_sessao`).
- **`src/aurora/tools.py`, `apartamento_da_sessao(tool_context, repo)`:** é a única fonte do apartamento para as tools. A função lê o state e confere com a tabela `sessoes` pelo `session.id`; se os valores divergirem, levanta erro. **Nenhuma tool tem parâmetro de apartamento**, e um teste verifica isso nas assinaturas.
- **`cancelar_minha_reserva`** procura o alvo só entre `repo.reservas_do_apartamento(apartamento)`, e `CondominioRepository.cancelar_reserva` (`db.py`) ainda filtra `WHERE codigo = ? AND apartamento = ?`. Se a reserva não for do apartamento, a resposta é neutra (`nao_encontrada`): não diz se existe reserva de outro apartamento nem traz o código dela.
- **`consultar_disponibilidade`** e a checagem prévia de `reservar_area` devolvem só `disponivel: true/false` ou `indisponivel`, nunca o dono nem o código da reserva.

**Por que não depende do modelo:** o modelo não tem como passar outro apartamento, porque nenhuma tool recebe esse dado. Nenhuma tool grava o state e as rotas não permitem alterá-lo. Mesmo o LLM falso "malicioso" dos testes, que chama `cancelar_minha_reserva(codigo="RSV-4821")` numa sessão do 101, não cancela nada.

### Garantia 3: nada se perde no reinício

- **`src/aurora/service.py`, `AuroraService.__init__`:** usa `DatabaseSessionService(db_url="sqlite+aiosqlite:///var/sessoes.db")`. Sessões, eventos e state ficam em disco.
- **`src/aurora/db.py`:** reservas, cancelamentos (status `cancelada`, a linha é mantida) e visitantes ficam em `var/condominio.db`. A subida só carrega `dados/` se o banco estiver vazio (`repo.esta_vazio()`), então reiniciar a API não restaura nada.
- Uma confirmação pedida antes do reinício pode ser aprovada depois dele, porque as pendentes são lidas dos eventos persistidos (teste `test_g1_confirmacao_aprovada_apos_reinicio`).

**Por que não depende do modelo:** a persistência é feita pela infraestrutura, Runner com serviço de sessão em banco e repositório SQLite.

### Garantia 4: o regulamento é consultado, não carregado

- **`src/aurora/agents.py`, `INSTRUCAO_PRINCIPAL`:** o agente principal não recebe nenhum trecho do regulamento. As instruções só dizem para usar a tool `especialista_regulamento`.
- **`src/aurora/agents.py`, `build_root_agent`:** `tools=[AgentTool(agent=especialista_regulamento)]`. O especialista roda numa sessão em memória isolada. Na sessão do morador ficam só a chamada (`functionCall` com a pergunta) e a resposta curta (`functionResponse`).
- **`src/aurora/regulamento.py`, `buscar_capitulo` / `escolher_capitulo`, e `tools.py`, `consultar_regulamento`:** o código divide `dados/regulamento.md` por capítulo (`## `) e devolve **um único capítulo**, escolhido pelo título ou por relevância. Nem o especialista recebe o regulamento inteiro.

**O que o código garante:** o texto do regulamento só circula na sessão em memória do `AgentTool`, e cada chamada de `consultar_regulamento` devolve um único capítulo. Na sessão do morador entra apenas a resposta final do especialista, que é instruído a responder de forma curta. O teste `test_g4_eventos_nao_contem_outros_capitulos` procura trechos de todos os outros capítulos nos eventos.

### Garantia 5: dois moradores, uma reserva

- **`src/aurora/db.py`, `SCHEMA`:**
  ```sql
  CREATE UNIQUE INDEX IF NOT EXISTS ux_reservas_area_data_ativa
      ON reservas(area, data) WHERE status = 'ativa';
  ```
- **`src/aurora/db.py`, `criar_reserva`:** faz o `INSERT` dentro de `BEGIN IMMEDIATE`. Se o índice recusar (`IntegrityError` em `reservas.area, reservas.data`), devolve `ResultadoReserva("ocupada")`, e a tool responde normalmente `indisponivel`, com HTTP 200.

**Por que não depende do modelo nem da conferência prévia:** a conferência de agenda em `reservar_area` só evita pedir confirmação à toa. Quem impede a duplicata é o banco, no instante da gravação. Os testes cobrem 16 threads disputando a mesma data, um `INSERT` direto que ignora a agenda e duas aprovações concorrentes (no serviço e pelo cliente de teste da API).

**Regra de negócio 5 (códigos únicos):** o código `RSV-XXXXXX` é aleatório e passa pela tabela `codigos_emitidos` (`PRIMARY KEY`). Reservas canceladas mantêm a linha e o código, e um código já emitido nunca é reutilizado.

---

## Como rodar

### Pré-requisitos
- [uv](https://docs.astral.sh/uv/). O Python 3.12 é instalado pelo uv se necessário.
- Chave da Gemini API do [Google AI Studio](https://aistudio.google.com/apikey).
- Nenhum serviço externo: o armazenamento é SQLite local.

### Variáveis do `.env`

```bash
cp .env.example .env
```

| Variável | Obrigatória | Descrição |
|---|---|---|
| `GOOGLE_API_KEY` | sim | Chave do Google AI Studio. |
| `AURORA_MODELO` | não | Modelo Gemini de todos os agentes (padrão `gemini-3.6-flash`). |
| `AURORA_MODELO_PRINCIPAL` / `AURORA_MODELO_ESPECIALISTAS` | não | Modelo por papel (padrão: `AURORA_MODELO`). |
| `AURORA_VAR_DIR` | não | Pasta dos bancos SQLite (padrão `./var`). |
| `AURORA_PORT` | não | Porta da API (padrão `8000`). |

### Instalar, restaurar e subir

```bash
uv sync                    # instala as dependências (google-adk==2.9.1 fixado)
uv run aurora-restaurar    # volta reservas e visitantes ao estado de dados/
uv run aurora-api          # sobe a API em http://localhost:8000 (Ctrl+C para parar)
```

- `uv run aurora-restaurar` restaura apartamentos, áreas, reservas e visitantes e **mantém as sessões**. Com `uv run aurora-restaurar --sessoes`, também apaga todas as sessões.
- Na primeira subida, se o banco não existir, os dados iniciais são carregados automaticamente.
- Reiniciar a API (Ctrl+C e `uv run aurora-api`) preserva sessões, eventos e dados.

### Exemplo rápido

```bash
curl -s -X POST localhost:8000/sessoes -H 'content-type: application/json' -d '{"apartamento":"101"}'
curl -s -X POST localhost:8000/sessoes/<id>/mensagens -H 'content-type: application/json' \
     -d '{"texto":"Reserve o salão de festas para 2030-04-20"}'
curl -s -X POST localhost:8000/sessoes/<id>/confirmacoes -H 'content-type: application/json' \
     -d '{"id":"<id da confirmação>","confirmado":true}'
curl -s localhost:8000/apartamentos/101/reservas
```

Se o provedor do modelo falhar (chave ausente, cota, rede), as rotas de conversa respondem
`502` com a causa. As rotas de verificação funcionam sem chave.

### Fluxo do avaliador automatizado

`python3 scripts/fluxo_avaliador.py` executa os passos 1 a 14 do enunciado por HTTP contra a API real
(restaura os dados, sobe e reinicia a API, dispara as aprovações simultâneas). Na execução de 2026-11-09,
a partir de um clone limpo e com `gemini-3.6-flash`, as 37 verificações do script passaram. Como o fluxo
depende do modelo, o resultado pode variar entre execuções.

Para validação local sem chave do AI Studio existe um modo opcional `AURORA_PROVEDOR=openai` (extra `openai`
do `pyproject.toml`); o desafio exige Gemini, que é o padrão.

### Testes (sem chave de API)

```bash
uv run pytest
```

São 26 testes que usam um LLM falso roteirizado (`tests/fake_llm.py`). Eles validam o código das garantias
(`tests/test_garantias.py`), o encadeamento do fluxo do avaliador (`tests/test_fluxo_avaliador.py`) e o contrato da API
(`tests/test_contrato_api.py`), não o comportamento do Gemini.
