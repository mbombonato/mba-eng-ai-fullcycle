<details>
<summary>Phase 1 — Project Analysis (contexto)</summary>

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (3.13 no ambiente de validação; versão não fixada no projeto)
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1
Database:      SQLite via driver nativo sqlite3 (SQL manual), arquivo loja.db
Domain:        E-commerce API (produtos, usuários, pedidos, relatório de vendas)
Architecture:  Monolito sem camadas — 4 arquivos; models.py concentra SQL + regras de 4 domínios,
               app.py mistura roteamento com handlers administrativos que executam SQL
Entry point:   app.py (python app.py, porta 5000)
Source files:  4 files analyzed (~780 lines)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Endpoints:     19 routes
================================
```

| METHOD | PATH | HANDLER | FILE:LINE |
|---|---|---|---|
| GET | /produtos | controllers.listar_produtos | app.py:11 |
| GET | /produtos/busca | controllers.buscar_produtos | app.py:12 |
| GET | /produtos/<id> | controllers.buscar_produto | app.py:13 |
| POST | /produtos | controllers.criar_produto | app.py:14 |
| PUT | /produtos/<id> | controllers.atualizar_produto | app.py:15 |
| DELETE | /produtos/<id> | controllers.deletar_produto | app.py:16 |
| GET | /usuarios | controllers.listar_usuarios | app.py:18 |
| GET | /usuarios/<id> | controllers.buscar_usuario | app.py:19 |
| POST | /usuarios | controllers.criar_usuario | app.py:20 |
| POST | /login | controllers.login | app.py:21 |
| POST | /pedidos | controllers.criar_pedido | app.py:23 |
| GET | /pedidos | controllers.listar_todos_pedidos | app.py:24 |
| GET | /pedidos/usuario/<usuario_id> | controllers.listar_pedidos_usuario | app.py:25 |
| PUT | /pedidos/<pedido_id>/status | controllers.atualizar_status_pedido | app.py:26 |
| GET | /relatorios/vendas | controllers.relatorio_vendas | app.py:28 |
| GET | /health | controllers.health_check | app.py:30 |
| GET | / | index | app.py:32 |
| POST | /admin/reset-db | reset_database | app.py:47 |
| POST | /admin/query | executar_query | app.py:59 |

</details>

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code
Date:    2026-11-09
```

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 6 |
| HIGH | 5 |
| MEDIUM | 4 |
| LOW | 4 |
| **Total** | **19** |

## Findings

### F-01 [CRITICAL] SQL Injection em praticamente todas as queries (AP-02)
- **File:** `models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 149-151, 155, 157-161, 163-166, 174, 188, 192, 220, 224, 279-281, 289-297`
- **Description:** As queries são montadas por concatenação de strings com dados vindos do request, ex.: `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"` (models.py:110) e `" AND (nome LIKE '%" + termo + "%' ..."` (models.py:291).
- **Impact:** Bypass de autenticação confirmado no baseline (`POST /login` com `email = "admin@loja.com' --"` retorna 200 com o usuário admin); leitura/alteração arbitrária do banco; cadastro de produto legítimo com aspas (`Copo d'água`) quebra com 500.
- **Recommendation:** Usar placeholders `?` do sqlite3 em todas as queries; montar filtros dinâmicos só com cláusulas fixas + lista de parâmetros → Playbook P-02

### F-02 [CRITICAL] Endpoints administrativos executam SQL arbitrário e resetam o banco sem autenticação (AP-04)
- **File:** `app.py:47-57, 59-78`
- **Description:** `POST /admin/query` executa qualquer SQL recebido em `{"sql": ...}` (`cursor.execute(query)`, app.py:69) e `POST /admin/reset-db` apaga todas as tabelas; nenhuma das rotas verifica identidade ou permissão.
- **Impact:** Qualquer cliente anônimo exfiltra a base (incluindo senhas em texto puro) ou destrói todos os dados com uma requisição.
- **Recommendation:** Remover `/admin/query` (não há forma segura de expor SQL arbitrário); proteger `/admin/reset-db` com middleware de autorização por token de admin vindo do ambiente → Playbook P-14

### F-03 [CRITICAL] Credenciais e segredos hardcoded (AP-01)
- **File:** `app.py:7, controllers.py:289, database.py:76-78`
- **Description:** `SECRET_KEY = "minha-chave-super-secreta-123"` fixo no código e repetido na resposta do health check; seed cria o admin com senha fixa `admin123`.
- **Impact:** Segredo versionado permite forjar sessões/assinaturas; impossível rotacionar por ambiente; credencial de admin conhecida publicamente.
- **Recommendation:** Ler `SECRET_KEY` e demais configurações de variáveis de ambiente em `config/settings.py`, com `.env.example` sem valores reais → Playbook P-01

### F-04 [CRITICAL] Senhas armazenadas e comparadas em texto puro (AP-05)
- **File:** `models.py:109-111, 126-129, database.py:75-83`
- **Description:** `criar_usuario` grava a senha recebida sem hash; o login compara `senha = '<input>'` direto no SQL; o seed insere senhas em claro.
- **Impact:** Qualquer vazamento do banco (trivial via F-02) expõe as senhas reais dos clientes.
- **Recommendation:** Hash adaptativo com salt (`werkzeug.security.generate_password_hash`/`check_password_hash`, já disponível com o Flask); login busca por e-mail e verifica o hash → Playbook P-04

### F-05 [CRITICAL] Exposição de dados sensíveis nas respostas (AP-06)
- **File:** `models.py:83, 99, controllers.py:285-289`
- **Description:** `GET /usuarios` e `GET /usuarios/<id>` devolvem o campo `senha`; `GET /health` devolve `secret_key`, `db_path`, `debug` e `ambiente`.
- **Impact:** Vazamento direto de senhas e do segredo da aplicação para qualquer cliente.
- **Recommendation:** Serializar usuários por whitelist de campos na view; health check apenas com status e contagens → Playbook P-11

### F-06 [CRITICAL] God File: models.py concentra dados, regras e formatação de 4 domínios (AP-03)
- **File:** `models.py:1-314, app.py:47-78`
- **Description:** Um único módulo contém SQL, regra de estoque/total do pedido (models.py:139-146), regra de desconto do relatório (models.py:256-262) e conversão row→dict para produtos, usuários, pedidos e relatórios; `app.py` mistura configuração, roteamento e handlers com SQL.
- **Impact:** Viola SRP; impossível testar regras sem banco; qualquer mudança em um domínio arrisca os demais.
- **Recommendation:** Decompor em `models/` por agregado, `services/` para regras (pedido, relatório), `controllers/`, `views/` (rotas + serializers) e composition root → Playbook P-03

### F-07 [HIGH] Modo debug e bind público fixos no código; CORS irrestrito (AP-10)
- **File:** `app.py:8-9, 88`
- **Description:** `app.config["DEBUG"] = True` e `app.run(host="0.0.0.0", port=5000, debug=True)`; `CORS(app)` libera qualquer origem.
- **Impact:** O debugger do Werkzeug exposto na rede permite execução remota de código; configuração não varia por ambiente.
- **Recommendation:** Flags vindas do ambiente com default seguro (`FLASK_DEBUG=0`, `HOST=127.0.0.1`), origens CORS configuráveis → Playbook P-01

### F-08 [HIGH] Estado global mutável: conexão única compartilhada entre threads (AP-08)
- **File:** `database.py:4-11`
- **Description:** `global db_connection` criado uma vez com `check_same_thread=False` e reutilizado por todas as requisições; `db_path` fixo em variável de módulo.
- **Impact:** Condições de corrida entre requisições concorrentes; transações de uma requisição afetam outra; testes não conseguem isolar o banco.
- **Recommendation:** Conexão por requisição via `flask.g` + `teardown_appcontext`, caminho do banco vindo da config → Playbook P-08

### F-09 [HIGH] Acoplamento direto à infraestrutura sem injeção de dependência (AP-09)
- **File:** `models.py:1, 5, 25, 44, 55, 66, 73, 90, 106, 123, 134, 172, 204, 236, 276, 286, controllers.py:3, 266, app.py:4, 49, 66`
- **Description:** Todas as camadas (models, controllers e app) importam e chamam `get_db()` diretamente; o controller de health executa SQL.
- **Impact:** Impossível substituir o banco em testes; controllers dependem de detalhes de persistência (viola DIP e MVC).
- **Recommendation:** Composition root (`create_app`) configura a conexão; só a camada de models acessa o banco → Playbook P-08

### F-10 [HIGH] Regras de negócio e side effects nos controllers (AP-07)
- **File:** `controllers.py:28-54, 72-90, 208-210, 247-250`
- **Description:** Controllers validam regras de domínio (categorias válidas, limites de nome), simulam envio de e-mail/SMS/push com `print` e disparam notificações por mudança de status.
- **Impact:** Regra presa ao HTTP, duplicada e impossível de reutilizar/testar isoladamente.
- **Recommendation:** Extrair validação para um módulo de validators e regras/notificações para `services/` → Playbook P-07, P-16

### F-11 [HIGH] Criação de pedido em múltiplas escritas sem transação explícita (AP-12)
- **File:** `models.py:133-169`
- **Description:** Insere o pedido, depois cada item e baixa o estoque em loop, relendo o preço a cada item; não há `BEGIN/ROLLBACK` — uma falha no meio do segundo loop deixa pedido sem itens ou estoque baixado parcialmente. A quantidade não é validada (quantidade negativa **aumenta** o estoque e gera total negativo).
- **Impact:** Inconsistência de dados financeiros e de estoque.
- **Recommendation:** Validar itens antes de escrever e executar todas as escritas em uma transação (`with conn:`) → Playbook P-09, P-16

### F-12 [MEDIUM] Queries N+1 na listagem de pedidos e no relatório (AP-13)
- **File:** `models.py:171-201, 203-233, 239-254`
- **Description:** Para cada pedido, uma query de itens; para cada item, uma query do nome do produto (1 + N + N·M). O relatório faz 5 consultas separadas que caberiam em uma agregação.
- **Impact:** Latência cresce linearmente com o volume de pedidos.
- **Recommendation:** JOIN `itens_pedido` × `produtos` em uma única query e agrupar em memória; agregação com `SUM(CASE ...)` → Playbook P-06

### F-13 [MEDIUM] Código duplicado (AP-15)
- **File:** `models.py:12-21, 31-40, 304-313, 178-199, 210-231, controllers.py:28-50, 72-90`
- **Description:** Conversão row→dict de produto repetida 3×; montagem de pedidos com itens repetida integralmente em `get_pedidos_usuario` e `get_todos_pedidos`; validação de produto copiada (e divergente: o update não valida nome nem categoria).
- **Impact:** Correções precisam ser replicadas; comportamento já diverge entre create e update.
- **Recommendation:** Serializer único por entidade; uma função de montagem de pedidos; validador único com modo parcial → Playbook P-07, P-16

### F-14 [MEDIUM] Tratamento de erros descentralizado que vaza detalhes internos (AP-16)
- **File:** `controllers.py:10, 21, 60, 95, 108, 125, 133, 143, 164, 185, 218, 226, 234, 254, 261, 291, app.py:77`
- **Description:** 17 blocos `except Exception as e: return jsonify({"erro": str(e)}), 500` copiados em cada handler.
- **Impact:** Mensagens internas (SQL, stack) vão para o cliente; erros de entrada (ex.: corpo vazio no login → `AttributeError`) viram 500.
- **Recommendation:** Exceções de domínio (`ValidationError`, `NotFoundError`...) + error handler central registrado no app → Playbook P-05

### F-15 [MEDIUM] Validação de entrada ausente ou incompleta (AP-14)
- **File:** `controllers.py:43-46, 157, 169-171, 195-201, 239-245`
- **Description:** `preco`/`estoque` não têm tipo verificado (`"10" < 0` → `TypeError` 500); login e atualização de status não tratam corpo ausente; e-mail sem formato nem unicidade; itens do pedido sem validação de `produto_id`/`quantidade`; atualizar status de pedido inexistente retorna 200.
- **Impact:** Erros 500 para entradas inválidas e dados corrompidos (e-mails duplicados, quantidades negativas).
- **Recommendation:** Camada de validação por recurso, retornando 400/404/409 coerentes → Playbook P-16

### F-16 [LOW] `print` usado como logging (AP-23)
- **File:** `controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250, app.py:56, 83-86`
- **Description:** 19 chamadas `print`, inclusive registrando e-mails de usuários em tentativas de login.
- **Impact:** Sem níveis, sem destino configurável; dados pessoais em stdout.
- **Recommendation:** `logging.getLogger(__name__)` com níveis → Playbook P-15

### F-17 [LOW] Magic numbers e strings de domínio espalhados (AP-21)
- **File:** `models.py:257-262, controllers.py:47-52, 242, 285-286`
- **Description:** Faixas e percentuais de desconto (`10000`, `0.1`, `5000`, `0.05`...), limites de nome (`2`, `200`), lista de categorias e de status, versão `"1.0.0"` e ambiente `"producao"` literais.
- **Impact:** Regras de negócio escondidas e duplicadas; mudar uma regra exige caça no código.
- **Recommendation:** Constantes nomeadas em `config/constants.py` → Playbook P-13

### F-18 [LOW] Nomenclatura ruim e sombra de builtins (AP-22)
- **File:** `models.py:24, 54, 65, 89, 187, 191, 219, 223, controllers.py:56, 160`
- **Description:** Parâmetros/variáveis chamados `id` (sombra do builtin) e cursores numerados `cursor2`, `cursor3`.
- **Impact:** Legibilidade e risco de bugs sutis.
- **Recommendation:** Nomes descritivos (`produto_id`, `itens_rows`) ao extrair as camadas → Playbook P-03

### F-19 [LOW] Imports não utilizados (AP-24)
- **File:** `models.py:2, database.py:2`
- **Description:** `import sqlite3` em models.py e `import os` em database.py nunca são usados.
- **Impact:** Ruído e falsa impressão de dependência.
- **Recommendation:** Remover durante a refatoração.

## Deprecated APIs

none detected — verificado contra Flask 3.1.1, flask-cors 5.0.1 e stdlib `sqlite3` (Python 3.12+: os
conversores padrão de `TIMESTAMP`, deprecated, só atuam com `detect_types`, que o projeto não usa).

## Proposed target structure

```
code-smells-project/
├── app.py                         # entry point fino (python app.py)
├── .env.example
├── src/
│   ├── app.py                     # composition root: create_app()
│   ├── config/{settings.py, constants.py}
│   ├── database/{connection.py, schema.py}
│   ├── models/{produto_model.py, usuario_model.py, pedido_model.py}
│   ├── services/{pedido_service.py, relatorio_service.py, notificacao_service.py}
│   ├── controllers/{produto, usuario, pedido, relatorio, sistema}_controller.py + validators.py
│   ├── views/{routes.py, serializers.py}
│   └── middlewares/{error_handler.py, auth.py}
└── tests/smoke.json
```

```
================================
Total: 19 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
