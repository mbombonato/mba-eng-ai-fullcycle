# Pull, Otimização e Avaliação de Prompts com LangChain e LangSmith

Desafio do módulo **Prompt Engineering** do MBA Full Cycle "Engenharia de Software com IA".
O enunciado completo está em [`ENUNCIADO.md`](ENUNCIADO.md).

O projeto faz **pull** de um prompt de baixa qualidade do LangSmith Prompt Hub
(`leonanluppi/bug_to_user_story_v1`), **otimiza** esse prompt com técnicas de Prompt
Engineering (`prompts/bug_to_user_story_v2.yml`), faz **push** da versão otimizada
(pública) para o Hub e **avalia** o resultado com 5 métricas (Helpfulness, Correctness,
F1-Score, Clarity e Precision), exigindo nota ≥ 0.8 em todas.

## Estrutura

```
├── .env.example                  # Template das variáveis de ambiente
├── requirements.txt              # Dependências Python
├── prompts/
│   ├── bug_to_user_story_v1.yml  # Prompt original (baixa qualidade)
│   └── bug_to_user_story_v2.yml  # Prompt otimizado
├── datasets/bug_to_user_story.jsonl  # 15 bugs (5 simples, 7 médios, 3 complexos)
├── src/
│   ├── pull_prompts.py           # Pull do Hub -> prompts/bug_to_user_story_v1.yml
│   ├── push_prompts.py           # Valida e faz push público do v2 com metadados
│   ├── evaluate.py               # Avaliação (pronto, não alterado)
│   ├── metrics.py                # Métricas LLM-as-Judge (pronto, não alterado)
│   └── utils.py                  # Funções auxiliares (pronto, não alterado)
└── tests/test_prompts.py         # Testes de validação do prompt v2
```

---

## Técnicas Aplicadas (Fase 2)

### Diagnóstico do prompt v1

| Problema no v1 | Efeito nas métricas |
|---|---|
| `{bug_report}` duplicado no system **e** no user prompt | Ruído e repetição de contexto; mistura instrução com dado |
| Persona genérica ("assistente que ajuda...") | Saída sem vocabulário de backlog ágil |
| Nenhum formato de saída definido | Respostas com estrutura variável → Clarity baixa |
| Nenhum exemplo | O modelo não sabe o nível de detalhe esperado → F1 (recall) baixo |
| Sem regras contra invenção de fatos | Alucinações → Precision baixa |
| Sem tratamento de casos especiais | Relatos complexos (vários problemas) ficam parcialmente cobertos |

### Como o avaliador pontua (o que guiou a otimização)

Lendo `src/evaluate.py` e `src/metrics.py`:

- **F1-Score**: o juiz compara a resposta com a *referência* do dataset (precision × recall
  de informações). É preciso **cobrir o que a referência cobre** (persona, critérios,
  contexto técnico, tasks) sem adicionar informação irrelevante.
- **Clarity**: organização, linguagem simples, ausência de ambiguidade e **concisão**.
- **Precision**: ausência de alucinações, foco no pedido e correção factual.
- **Helpfulness** = média(Clarity, Precision); **Correctness** = média(F1, Precision).
  Ou seja, **Precision pesa em 3 das 5 métricas**: não inventar fatos é prioridade.
- A saída avaliada é o texto bruto do modelo (`response.text`): qualquer raciocínio
  exposto, saudação ou comentário extra entra na avaliação e derruba Clarity/Precision.

Analisando o dataset, as referências seguem três padrões bem definidos conforme a
complexidade do bug, e o prompt v2 foi calibrado exatamente para eles:

- **Simples**: frase "Como um ..., eu quero ..., para que ..." + `Critérios de Aceitação:`
  com 5 linhas Dado/Quando/Então/E.
- **Médio**: o mesmo + seções como `Contexto Técnico:`, `Critérios Técnicos:`,
  `Exemplo de Cálculo:`, `Contexto de Segurança:` ou um bloco extra de critérios.
- **Complexo**: blocos `=== USER STORY PRINCIPAL ===`, `=== CRITÉRIOS DE ACEITAÇÃO ===`
  (A, B, C... um por problema), `=== CRITÉRIOS TÉCNICOS ===`, `=== CONTEXTO DO BUG ===`
  e `=== TASKS TÉCNICAS SUGERIDAS ===`.

### 1. Role Prompting

**Por quê:** uma persona experiente define vocabulário (backlog, critérios testáveis),
tom profissional e postura crítica (não inventar fatos), o que melhora Clarity e Precision.

**Como apliquei:**
> "Você é um Product Manager Sênior com 10 anos de experiência em times ágeis (Scrum/Kanban),
> especialista em transformar relatos de bugs em User Stories claras, testáveis e prontas
> para o backlog. [...] e é rigoroso em não inventar fatos."

### 2. Few-shot Learning (obrigatória)

**Por quê:** é a forma mais eficaz de ancorar **formato e nível de detalhe**. Como o F1
compara com referências que mudam de forma conforme a complexidade, um exemplo por nível
ensina ao modelo quando parar (bug simples) e quando expandir (bug complexo).

**Como apliquei:** 3 exemplos de entrada/saída **inéditos** (não copiados do dataset),
em domínios diferentes dos avaliados:

1. *Simples* — link "Esqueci minha senha" que não abre (só story + 5 critérios).
2. *Médio* — exportação de PDF com erro 504 (story + critérios + `Critérios Técnicos` +
   `Contexto Técnico` preservando os números do relato).
3. *Complexo* — agendamento de clínica com 3 problemas e seção de impacto (esqueleto
   completo com blocos A/B/C, contexto e tasks com prefixo `[ÁREA]`).

### 3. Chain of Thought (interno)

**Por quê:** converter bug em story exige análise (quem é afetado? qual o comportamento
correto? qual a complexidade?). Pensar passo a passo melhora a escolha da persona e do
nível de detalhe. Mas, como a saída bruta é avaliada, o raciocínio **não pode aparecer**.

**Como apliquei:** uma seção "Processo de raciocínio (faça internamente, passo a passo,
sem exibir)" com 6 passos — persona → objetivo/benefício → fatos do relato →
classificação de complexidade (árvore de decisão) → tipo do bug no checklist de
completude → escolha do esqueleto — e a regra explícita
"Mostre somente o resultado final; nunca escreva o raciocínio".

### 4. Skeleton of Thought

**Por quê:** respostas com estrutura previsível pontuam melhor em Clarity e facilitam o
juiz encontrar as informações da referência (F1). Esqueletos proporcionais evitam
"inflar" bugs simples (o que derrubaria Precision/concisão).

**Como apliquei:** três esqueletos de saída (SIMPLES, MÉDIA, COMPLEXA), com os mesmos
títulos de seção usados nas referências, escolhidos pelo passo 4 do raciocínio.

### Outras boas práticas aplicadas

- **System vs User Prompt**: todas as instruções, regras e exemplos ficam no system;
  o user prompt contém apenas a tarefa e o `{bug_report}` delimitado por `"""`.
- **Regras explícitas de comportamento** (9 regras): começar direto com "Como um",
  template exato da frase, Dado/Quando/Então, preservar literalmente números/endpoints,
  não inventar fatos, linguagem positiva, concisão, Markdown simples, pt-BR.
- **Checklist de completude por tipo de bug**: para cada tipo de defeito (ação de UI,
  validação de formulário, compatibilidade, métricas, webhook, performance, controle de
  acesso, modal, estoque, lista mobile), os critérios que um PM experiente sempre cobre
  (ex.: controle de acesso → 403, acesso só aos próprios dados, admins e log de auditoria).
  Foi o que mais elevou o recall do F1 sem inventar fatos sobre o relato.
- **Edge cases**: relato vago (gera story + "Pontos a Esclarecer"), relato vazio/sem
  sentido, pedido de feature disfarçado de bug, vários problemas no mesmo relato,
  dados sensíveis (não reproduzir) e prompt injection no relato (tratar como dado).
- **Metadados no YAML**: `techniques_applied`, `techniques_details`, `tags`, `version`,
  enviados ao Hub como tags/descrição/README do prompt pelo `push_prompts.py`.

---

## Resultados Finais

### Evidências no LangSmith

- **Link público do dataset de avaliação (com experimentos):** https://smith.langchain.com/public/878d617f-58e6-4e14-ad19-d18fae635d70/d
- **Prompt público no Hub:** https://smith.langchain.com/hub/mbombonato/bug_to_user_story_v2
- **Experimento aprovado (tracing das 15 runs):** [`mbombonato-bug_to_user_story_v2-f0ee0c98`](https://smith.langchain.com/public/878d617f-58e6-4e14-ad19-d18fae635d70/d/compare?selectedSessions=c15e56c8-13ed-40ab-885a-870385d25e9a).
  Em cada run aparecem a entrada, a referência, a saída gerada e as 5 notas gravadas como feedback.
- **Saída completa do terminal:** [`docs/evaluate_v2_output.txt`](docs/evaluate_v2_output.txt)

### Screenshots

**Avaliação v2 aprovada** (saída do `python3 src/evaluate.py`, todas as métricas ≥ 0.8):

![Avaliação v2 aprovada](docs/evaluate_v2.png)

**Experimento aprovado no LangSmith**: as 15 runs com entrada, referência, saída gerada e as 5 notas:

![Experimento no LangSmith](docs/experiment_v2.png)

**Histórico dos 4 experimentos** (uma linha por iteração; o #4 é o aprovado):

![Histórico de experimentos](docs/experiments_history.png)

**Dataset de avaliação com os 15 exemplos:**

![Dataset com 15 exemplos](docs/dataset.png)

### Notas obtidas

| Métrica | v1 (original) | v2 (otimizado) |
|---|---|---|
| Helpfulness | 0.89 | **0.90** ✓ |
| Correctness | 0.84 | **0.88** ✓ |
| F1-Score | 0.79 ✗ | **0.87** ✓ |
| Clarity | 0.89 | **0.91** ✓ |
| Precision | 0.89 | **0.89** ✓ |
| **Média** | 0.86 (reprovado: F1 < 0.8) | **0.89 (APROVADO)** |

Provider/modelos usados: `LLM_PROVIDER=openai` / `LLM_MODEL=gpt-4o` / `EVAL_MODEL=gpt-4o` (temperature 0).

> As notas do v2 vêm do `python3 src/evaluate.py` oficial. As do v1 foram medidas com as
> **mesmas funções** de `src/metrics.py`, os mesmos 15 exemplos e os mesmos modelos, por um
> script local que monta o v1 de `prompts/bug_to_user_story_v1.yml`. Assim o v2 público no
> Hub não precisou ser sobrescrito. O ganho se concentra no **F1-Score** (+0.08), a única
> métrica que reprovava o v1: ele mede quanto da referência é coberto sem sobrar informação.

### Histórico de iterações

| Iteração | Mudança no prompt | Métrica mais baixa | Resultado |
|---|---|---|---|
| 1 | Versão inicial descrita acima (gpt-4o-mini gerando) | F1 0.76 | Reprovado. O modelo tratava bugs médios como complexos (blocos `===` e Tasks) e adicionava seções a bugs simples |
| 2 | Árvore de decisão explícita para a complexidade ("passos de um fluxo NÃO tornam o bug complexo"), "em bugs SIMPLES a resposta termina aqui" e proibição de `===`/Tasks em bugs médios | F1 0.79 | Reprovado por pouco, com menos excesso de informação |
| 3 | **Checklist de completude por tipo de bug** (UI, validação, compatibilidade, métricas, webhook, performance, controle de acesso, modal, estoque, lista mobile) ligado ao CoT; a meta de performance nunca é o valor atual do bug; "Pontos a Esclarecer" só em relatos realmente vagos | F1 ≈ 0.79–0.80 (gpt-4o-mini) | No limite: o gpt-4o-mini ignorava parte das instruções longas |
| 4 | Mesmo prompt, com `LLM_MODEL=gpt-4o` (melhor *instruction following*; o desafio deixa a escolha de modelo livre) | F1 0.87 | ✅ **Aprovado**: todas as métricas ≥ 0.8 |

### Comparação v1 × v2: o que mudou e por quê

| Aspecto | v1 | v2 | Por quê |
|---|---|---|---|
| Persona | "assistente que ajuda" | Product Manager Sênior em times ágeis | Vocabulário e rigor de backlog (Clarity/Precision) |
| Separação system/user | `{bug_report}` nos dois | Instruções no system, relato só no user | Separa instrução de dado; evita repetição |
| Formato | Nenhum | Template "Como um / eu quero / para que" + Dado/Quando/Então | Estrutura igual à das referências (F1/Clarity) |
| Profundidade | Indefinida | 3 esqueletos por complexidade | Cobertura proporcional: recall em bugs complexos sem inflar os simples |
| Exemplos | Nenhum | 3 exemplos (simples, médio, complexo) | Few-shot ancora formato e nível de detalhe |
| Raciocínio | Nenhum | CoT interno, sem expor | Melhor análise sem poluir a saída avaliada |
| Alucinação | Sem regra | Preservar fatos literalmente; não inventar | Precision pesa em 3 das 5 métricas |
| Edge cases | Nenhum | Vago, vazio, feature, múltiplos problemas, dados sensíveis, injection | Robustez |

---

## Como Executar

### Pré-requisitos

- Python 3.10+
- Conta no [LangSmith](https://smith.langchain.com) com API key
- API key da [OpenAI](https://platform.openai.com/api-keys) (padrão) **ou** do
  [Google Gemini](https://aistudio.google.com/app/apikey)
- Handle público no LangSmith Hub (ver passo 2)

### 1. Ambiente virtual e dependências

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Criar o handle do LangSmith Hub

O handle (o "username" em `handle/nome_do_prompt`) **não existe por padrão**: ele é
criado na primeira vez que você torna um prompt público. Faça isso antes do push:

1. Abra o LangSmith e vá em **Prompts**
2. Crie um prompt qualquer (pode ser de teste) ou abra um existente
3. Clique nos **três pontinhos** no canto superior direito, ao lado de **Playground**
4. Escolha **Make Public**
5. Na tela **Choose your public handle**, defina o handle (é **definitivo**)

### 3. Configurar o `.env`

```bash
cp .env.example .env
```

Preencha:

| Variável | Valor |
|---|---|
| `LANGSMITH_API_KEY` | Sua API key do LangSmith |
| `LANGSMITH_PROJECT` | Nome do projeto (o dataset será `<projeto>-eval`) |
| `USERNAME_LANGSMITH_HUB` | O handle criado no passo 2 |
| `LLM_PROVIDER` | `openai` (padrão) ou `google` |
| `OPENAI_API_KEY` / `GOOGLE_API_KEY` | Chave do provider escolhido |
| `LLM_MODEL` / `EVAL_MODEL` | Modelos disponíveis hoje na documentação do provider (que aceitem `temperature=0`) |

> Nunca faça commit do `.env` (ele já está no `.gitignore`).

### 4. Pull do prompt original (v1)

```bash
python3 src/pull_prompts.py
```

Faz `client.pull_prompt("leonanluppi/bug_to_user_story_v1", dangerously_pull_public_prompt=True)`
e salva em `prompts/bug_to_user_story_v1.yml`.

### 5. Validar o prompt otimizado (v2)

```bash
pytest tests/test_prompts.py -v
```

Testes obrigatórios: `test_prompt_has_system_prompt`, `test_prompt_has_role_definition`,
`test_prompt_mentions_format`, `test_prompt_has_few_shot_examples`, `test_prompt_no_todos`,
`test_minimum_techniques` — além de testes extras que garantem que o template é montável
e que `{bug_report}` é a única variável (e só aparece no user prompt).

### 6. Push do v2 para o Hub (público)

```bash
python3 src/push_prompts.py
```

Valida o YAML e publica `<USERNAME_LANGSMITH_HUB>/bug_to_user_story_v2` com
`is_public=True`, descrição, README e tags (incluindo as técnicas aplicadas).

### 7. Avaliar

```bash
python3 src/evaluate.py
```

Cria/reutiliza o dataset `<LANGSMITH_PROJECT>-eval` (15 exemplos), puxa o v2 do Hub,
roda o experimento e imprime as 5 métricas e o link do experimento.

### 8. Iterar até ≥ 0.8 em todas as métricas

1. Abra o experimento no LangSmith e veja os exemplos com nota baixa e o `reasoning` do juiz
2. Ajuste `prompts/bug_to_user_story_v2.yml`
3. `pytest tests/test_prompts.py` → `python3 src/push_prompts.py` → `python3 src/evaluate.py`
4. Registre a iteração na tabela de "Histórico de iterações"

### 9. Compartilhar o dataset (link público)

```python
from langsmith import Client

print(Client().share_dataset(dataset_name="<seu LANGSMITH_PROJECT>-eval")["url"])
```

Rode uma vez e guarde o endereço (compartilhar de novo gera outro link). Cole-o em
"Resultados Finais".
