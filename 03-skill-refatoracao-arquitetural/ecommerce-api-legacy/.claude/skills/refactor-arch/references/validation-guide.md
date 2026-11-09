# Guia de Validação (Fase 3)

A refatoração só está concluída quando há **evidência executada** de que a aplicação sobe e de que
todos os endpoints originais continuam respondendo. "Deve funcionar" não é validação.

## 1. Preparar o ambiente (sem poluir o repositório)

| Stack | Dependências | Observação |
|---|---|---|
| Python | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (ou `uv venv` + `uv pip install`) | `.venv/` deve estar no `.gitignore` |
| Node | `npm ci` (ou `npm install`) | `node_modules/` no `.gitignore`; não commite lockfiles de outro gerenciador |

Use **porta livre** e **banco temporário** (variável de ambiente para o caminho do banco quando
existir) para não sujar dados locais nem colidir com outros processos.

## 2. Spec de smoke test (`tests/smoke.json`)

Monte a partir do inventário de rotas da Fase 1. Para cada recurso:

- 1 caso de sucesso por rota (GET lista, GET item, POST, PUT, DELETE...), com `expect_keys` dos
  campos principais da resposta original (prova de contrato preservado);
- ≥ 1 caso de erro (404 de inexistente, 400 de validação);
- casos que **provam as correções** de segurança/robustez (ex.: login com `' --` deve dar 401;
  listagem de usuários com `forbid_keys: ["senha"]`; rota admin sem token deve dar 401/403;
  entrada com tipo errado deve dar 400, não 500);
- `capture` para encadear IDs criados (`{{produto_id}}`), `{{env:VAR}}` para segredos de teste.

Formato completo documentado no cabeçalho de `scripts/smoke_test.py`.

## 3. Baseline (ANTES de editar qualquer arquivo)

```bash
# exemplo Flask
DATABASE_PATH=/tmp/baseline.db flask --app app run --port 5101 &
python3 .claude/skills/refactor-arch/scripts/smoke_test.py tests/smoke.json \
  --base-url http://127.0.0.1:5101 --record /tmp/baseline.json
kill %1
```

Interprete: falhas no baseline devem corresponder **apenas** a findings do relatório (são a
prova do problema). Qualquer outra falha indica erro na spec — corrija a spec antes de refatorar.

## 4. Pós-refatoração

1. **Boot limpo:** suba com o comando de start documentado; o log não pode conter stacktrace,
   `Error`, `Traceback` ou `DeprecationWarning` originado do código do projeto.
   - Python: `python -W error::DeprecationWarning -c "import app"` ajuda a flagrar APIs deprecated remanescentes.
   - Node: `node --trace-deprecation src/server.js`.
2. **Smoke test:** rode a mesma spec; o resultado exigido é `N/N requisições OK`.
3. **Compare com o baseline:** para rotas de sucesso, as chaves do JSON devem ser as mesmas
   (exceto campos sensíveis removidos de propósito — liste-os em "Contract changes").
4. **Re-scan de anti-patterns:** reexecute os greps dos findings CRITICAL/HIGH
   (`anti-patterns-catalog.md`). Zero ocorrências esperadas, por exemplo:
   ```bash
   grep -rnE "execute\(.*(\+|f\")" --include=*.py .        # SQL concatenado
   grep -rnEi "(secret|passw|senha|pass|token|api_?key|key)\w*['\"]?\]?\s*[:=]\s*['\"][^'\"]+['\"]|(pk|sk)_live_" \
     --include=*.py --include=*.js . | grep -v -e node_modules -e .venv -e .claude   # segredos
   grep -rn "debug=True" --include=*.py .
   ```
   Leia cada ocorrência: interpolar **constantes do código** (lista fixa de colunas, nomes de
   tabela, placeholders `?` gerados) é aceitável; interpolar qualquer valor vindo do request não é.
5. **Iteração:** se algo falhar, corrija e repita os passos 1–4 (máx. 3 ciclos). Persistindo,
   reporte com `✗` e a causa.

## 5. Checklist de validação (copie preenchido no resumo/README)

```markdown
### Fase 1 — Análise
- [ ] Linguagem detectada corretamente
- [ ] Framework detectado corretamente
- [ ] Domínio da aplicação descrito corretamente
- [ ] Número de arquivos analisados condiz com a realidade

### Fase 2 — Auditoria
- [ ] Relatório segue o template definido nos arquivos de referência
- [ ] Cada finding tem arquivo e linhas exatos
- [ ] Findings ordenados por severidade (CRITICAL → LOW)
- [ ] Mínimo de 5 findings identificados
- [ ] Detecção de APIs deprecated incluída (se aplicável)
- [ ] Skill pausa e pede confirmação antes da Fase 3

### Fase 3 — Refatoração
- [ ] Estrutura de diretórios segue padrão MVC
- [ ] Configuração extraída para módulo de config (sem hardcoded)
- [ ] Models criados para abstrair dados
- [ ] Views/Routes separadas para visualização ou roteamento
- [ ] Controllers concentram o fluxo da aplicação
- [ ] Error handling centralizado
- [ ] Entry point claro
- [ ] Aplicação inicia sem erros
- [ ] Endpoints originais respondem corretamente
```
