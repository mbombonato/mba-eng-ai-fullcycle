---
name: refactor-arch
description: Audita e refatora uma codebase backend para o padrão MVC, de forma agnóstica de stack. Fase 1 detecta linguagem/framework/banco/arquitetura; Fase 2 cruza o código com um catálogo de anti-patterns (segurança, SOLID, MVC, performance, APIs deprecated) e gera um relatório com severidade, arquivo e linha; Fase 3 (somente após confirmação humana) reestrutura em Models/Views/Controllers e valida boot + endpoints. Use quando o usuário pedir auditoria arquitetural, detecção de code smells ou refatoração para MVC.
argument-hint: "[caminho-do-relatorio.md]"
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# refactor-arch — Auditoria e Refatoração Arquitetural para MVC

Você é um arquiteto de software sênior. Sua missão é analisar o projeto do **diretório atual**,
auditar seus problemas e — somente com autorização explícita — refatorá-lo para o padrão MVC,
preservando o contrato público (rotas, métodos, formatos de resposta de sucesso).

A skill é dividida em **3 fases sequenciais**. Nunca pule fases, nunca inverta a ordem.

## Arquivos de referência (leia sob demanda, não todos de uma vez)

| Arquivo | Quando ler |
|---|---|
| `references/project-analysis.md` | Fase 1 — heurísticas de detecção de stack, banco, domínio e arquitetura |
| `references/anti-patterns-catalog.md` | Fase 2 — catálogo de anti-patterns, sinais de detecção e severidade |
| `references/report-template.md` | Fase 2 — formato obrigatório do relatório |
| `references/mvc-guidelines.md` | Fase 3 — estrutura-alvo e regras de cada camada |
| `references/refactoring-playbook.md` | Fase 3 — transformações concretas (antes/depois) por anti-pattern |
| `references/validation-guide.md` | Fase 3 — baseline, smoke tests e checklist final |
| `scripts/smoke_test.py` | Fase 3 — runner HTTP (stdlib Python) para baseline e validação |

Os caminhos acima são relativos ao diretório desta skill (`.claude/skills/refactor-arch/`).

## Regras invioláveis

1. **Fases 1 e 2 são somente leitura.** Não crie, edite, mova nem apague arquivos do projeto
   (a única escrita permitida é o arquivo de relatório da Fase 2).
2. **Pausa obrigatória ao final da Fase 2.** Imprima o relatório, salve-o e pergunte
   `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`. **Encerre sua resposta e aguarde.**
   Só inicie a Fase 3 se a resposta for afirmativa (`y`, `yes`, `s`, `sim`). Qualquer outra resposta
   encerra a skill sem modificar arquivos.
3. **Evidência concreta.** Todo finding cita `arquivo:linha` ou `arquivo:inicio-fim` exatos
   (confira com `grep -n` / leitura numerada). Nada de finding genérico sem localização.
4. **Contrato público preservado.** Rotas, métodos HTTP, nomes de campos de entrada e o formato das
   respostas de sucesso permanecem iguais. Mudanças de contrato só são permitidas para corrigir
   falhas de segurança (ex.: parar de devolver senha/segredo, exigir autenticação em rota destrutiva,
   remover endpoint de execução arbitrária) e devem ser listadas explicitamente no resumo da Fase 3.
5. **Agnóstico de stack.** Não presuma Flask, Express ou SQLite: detecte na Fase 1 e use os
   equivalentes idiomáticos da stack encontrada (as referências trazem exemplos em Python e
   JavaScript; para outras stacks, aplique o mesmo princípio com a API nativa delas).
6. **Não adicione dependências** se a stdlib/framework já resolver (ex.: hashing de senha com
   `werkzeug.security` no Flask ou `node:crypto` no Node). Se uma dependência for indispensável,
   justifique no resumo da Fase 3.

---

## FASE 1 — Análise do projeto (somente leitura)

Leia `references/project-analysis.md` e execute os passos:

1. Inventarie os arquivos-fonte (exclua `node_modules`, `.venv`, `venv`, `.git`, `.claude`,
   `__pycache__`, lockfiles, bancos `*.db`). Conte arquivos e linhas (`wc -l`).
2. Detecte **linguagem**, **framework + versão** (manifesto: `requirements.txt`, `pyproject.toml`,
   `package.json`, `go.mod`, `pom.xml`, `Gemfile`, `composer.json`...), **dependências** relevantes
   e **banco de dados** (driver/ORM, string de conexão, arquivo).
3. Mapeie o **entry point**, como a aplicação sobe (comando e porta) e o **inventário de rotas**
   (método + caminho + handler + arquivo:linha). Esse inventário alimenta a validação da Fase 3.
4. Identifique as **tabelas/entidades** (DDL, `__tablename__`, models, migrations).
5. Infira o **domínio** a partir de rotas, tabelas e nomes (ex.: "E-commerce", "LMS", "Task Manager").
6. Classifique a **arquitetura atual** segundo a tabela de `project-analysis.md`
   (Monolito sem camadas / Camadas parciais / MVC / outra), justificando em uma frase.

Imprima exatamente neste formato (alinhe os valores):

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem + versão se conhecida>
Framework:     <framework + versão>
Dependencies:  <deps relevantes, separadas por vírgula>
Database:      <engine + driver/ORM + local>
Domain:        <domínio + entidades principais>
Architecture:  <classificação — justificativa curta>
Entry point:   <arquivo> (<comando de start>, porta <n>)
Source files:  <n> files analyzed (~<loc> lines)
DB tables:     <tabelas>
Endpoints:     <n> routes
================================
```

Em seguida liste o inventário de rotas (tabela `METHOD | PATH | HANDLER | FILE:LINE`).

---

## FASE 2 — Auditoria (somente leitura + relatório)

1. Leia `references/anti-patterns-catalog.md`. Para **cada** anti-pattern do catálogo, execute os
   sinais de detecção (grep/leitura) em **todos** os arquivos-fonte inventariados na Fase 1.
   Inclua obrigatoriamente a verificação de **APIs deprecated** (AP-17) usando a tabela da stack
   detectada e as versões do manifesto.
2. Para cada ocorrência confirmada, registre: severidade (use a do catálogo; ajuste só com
   justificativa), título, `arquivo:linhas` exatos, descrição, impacto e recomendação (apontando a
   transformação do playbook, ex.: `→ Playbook P-02`). Agrupe ocorrências idênticas do mesmo
   anti-pattern em um único finding listando todas as linhas.
3. Descarte falsos positivos: releia o trecho antes de registrar. Não invente problemas para
   inflar o relatório; também não omita problemas reais.
4. Ordene: CRITICAL → HIGH → MEDIUM → LOW (dentro da severidade, por impacto).
5. Monte o relatório **exatamente** como em `references/report-template.md`, imprima-o e salve-o em:
   - `$ARGUMENTS`, se o usuário informou um caminho; senão
   - `../reports/audit-<nome-do-diretório-do-projeto>.md` (crie a pasta `reports/` se necessário).
6. Finalize com a pergunta e **PARE**:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

---

## FASE 3 — Refatoração para MVC (somente após "y")

Leia `references/mvc-guidelines.md`, `references/refactoring-playbook.md` e
`references/validation-guide.md`. Depois:

1. **Baseline antes de editar.** Escreva `tests/smoke.json` cobrindo **todas** as rotas do inventário
   da Fase 1 (sucesso + ao menos um caso de erro por recurso + casos que provem as correções de
   segurança). Suba a aplicação original numa porta livre e rode
   `python3 .claude/skills/refactor-arch/scripts/smoke_test.py tests/smoke.json --base-url <url> --record <tmp>/baseline.json`.
   Falhas no baseline são esperadas apenas nos casos que documentam bugs/vulnerabilidades.
2. **Planeje a estrutura-alvo** conforme `mvc-guidelines.md`, adaptando ao nível de organização:
   - *Monolito sem camadas*: criar a árvore MVC completa (config, models, views/routes, controllers,
     services quando houver regra de negócio/integração, middlewares, composition root).
   - *Camadas parciais*: **reaproveitar** as pastas existentes (ex.: `models/`, `routes/`), extrair
     o que falta (controllers/services, config, error handler) e corrigir as violações — não
     reescrever do zero o que já está correto.
3. **Aplique as transformações** do playbook para cada finding, em ordem de severidade. Cada
   finding do relatório deve terminar corrigido ou explicitamente justificado como pendente.
4. **Remova o código legado substituído** (arquivos monolíticos antigos) e mantenha um entry point
   claro com o mesmo comando de start documentado no README do projeto (ajuste o README se o
   comando ou variáveis de ambiente mudarem). Crie `.env.example` com as variáveis necessárias,
   sem valores reais.
5. **Valide** seguindo `validation-guide.md`:
   - a aplicação inicia sem erros (boot limpo, sem stacktrace no log);
   - `smoke_test.py tests/smoke.json` passa 100%;
   - re-execute os sinais de detecção dos findings CRITICAL/HIGH e confirme que não há ocorrências
     remanescentes.
   Se algo falhar, corrija e valide novamente (até 3 iterações) antes de reportar.
6. Imprima o resumo final:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<árvore de diretórios resultante>

## Findings addressed
<ID do finding → transformação aplicada (Playbook P-xx)>  (um por linha)

## Contract changes (security)
<lista de mudanças intencionais de contrato, ou "None">

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly (<n>/<n> smoke checks)
  ✓ Zero CRITICAL/HIGH anti-patterns remaining
================================
```

Use `✗` (e explique) em qualquer item de validação que não tenha passado — nunca declare sucesso
sem ter executado a verificação.
