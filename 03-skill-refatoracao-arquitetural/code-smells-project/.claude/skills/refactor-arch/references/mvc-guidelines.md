# Guidelines de Arquitetura — MVC alvo (Fase 3)

Em uma API HTTP, o "V" do MVC não é HTML: a **View** é a camada que expõe o recurso — o
**roteamento** (mapeia método + caminho → controller) e a **apresentação** (serialização da
resposta). Controllers orquestram, Models encapsulam dados e regras do domínio.

## 1. Estrutura-alvo

Use a convenção idiomática da stack. Modelo de referência:

```
<projeto>/
├── <entry point>              # mantém o comando de start original (ex.: app.py, src/server.js)
├── .env.example               # variáveis necessárias, sem valores reais
├── src/  (ou raiz, se o projeto já organiza pastas na raiz)
│   ├── config/                # settings: lê ambiente, defaults seguros, constantes
│   ├── models/                # entidades + acesso a dados (repositório/ORM) por agregado
│   ├── services/              # regras de negócio e integrações (pagamento, notificação, relatórios)
│   ├── controllers/           # fluxo da requisição: valida entrada → chama model/service → escolhe view
│   ├── views/  (ou routes/)   # rotas/blueprints/routers + serializers/presenters
│   ├── middlewares/           # error handler central, autenticação/autorização
│   ├── database/ (opcional)   # conexão, schema, seed, transações
│   └── app.(py|js)            # composition root: create_app(config) monta e injeta tudo
└── tests/smoke.json           # spec de smoke test (validation-guide.md)
```

Adaptação ao ponto de partida:

| Ponto de partida | Estratégia |
|---|---|
| Monolito sem camadas | Criar `src/` com todas as camadas; o arquivo antigo vira entry point fino ou é removido |
| Camadas parciais | Manter as pastas que já existem com o papel correto (`models/`, `routes/` = views); acrescentar `controllers/`, `services/`, `config/`, `middlewares/`; mover código mal posicionado |
| Já em MVC | Apenas corrigir findings pontuais; não reestruturar por reestruturar |

## 2. Responsabilidades e proibições por camada

### Config
- **Faz:** ler variáveis de ambiente (`os.environ`, `process.env`, `.env`), definir defaults
  **seguros** (debug desligado), centralizar constantes de domínio (status válidos, limites).
- **Não faz:** conter segredos reais; ser lido por `os.environ` espalhado no código (só a config lê o ambiente).

### Models
- **Faz:** representar entidades e tabelas; executar queries **parametrizadas**; encapsular
  regras intrínsecas da entidade (`task.is_overdue()`, `user.check_password()`).
- **Não faz:** importar `request`/`req`/`res`, devolver respostas HTTP, ler o ambiente, enviar e-mail.
- Em SQL manual: um módulo/classe por agregado (`ProductModel`, `OrderModel`) recebendo a conexão por parâmetro/injeção.

### Services (parte do "M" — lógica de domínio)
- **Faz:** regras que envolvem mais de uma entidade ou integrações externas (checkout, cálculo de
  desconto, relatórios, gateway de pagamento, notificações); controlar transações de casos de uso.
- **Não faz:** conhecer HTTP (status code, `request`). Sinaliza erros com exceções de domínio.

### Controllers
- **Faz:** concentrar o **fluxo** de cada caso de uso: extrair e validar a entrada, chamar
  model/service, escolher a view/serializer e o status de sucesso.
- **Não faz:** SQL, regra de negócio pesada, `try/except` genérico em cada função (isso é do
  error handler), montar dicionário campo a campo (isso é da view/serializer).
- Tamanho-alvo: funções curtas (≲ 25 linhas).

### Views / Routes
- **Faz:** declarar rotas (método + caminho → controller), aplicar middlewares por rota
  (ex.: `require_admin`), serializar entidades por **whitelist** de campos.
- **Não faz:** lógica de negócio, acesso a banco.

### Middlewares
- **Error handler central:** converte exceções de domínio (`NotFoundError` → 404,
  `ValidationError` → 400, `ConflictError` → 409, `UnauthorizedError` → 401/403) e trata
  inesperadas com 500 genérico + log (sem vazar `str(e)`).
- **Auth:** valida token/credencial de admin com comparação em tempo constante.

### Composition root (`app.py` / `app.js`)
- Factory `create_app(config)` / `createApp(deps)`: carrega config, cria conexão/ORM, instancia
  models/services/controllers **injetando dependências**, registra rotas e error handler.
- Entry point (`if __name__ == "__main__"` / `server.js`) só chama a factory e sobe o servidor.

## 3. Regra de dependência

```
views/routes → controllers → services → models → database
        ↘ middlewares          ↘ config (todas podem ler config)
```

- Dependências apontam **para dentro**: models nunca importam controllers/views; services nunca importam o framework web.
- Nenhum estado mutável em nível de módulo além de objetos imutáveis/constantes e da extensão do
  ORM inicializada pelo factory (ex.: `db = SQLAlchemy()` do Flask-SQLAlchemy é aceitável).

## 4. Contrato de erro padronizado

Mantenha o formato de erro que o projeto já usava (ex.: `{"erro": "..."}` ou `{"error": "..."}`),
mas produza-o em **um único lugar** (error handler). Respostas de sucesso não mudam de formato.

## 5. Critérios de pronto da Fase 3

- [ ] Árvore de diretórios segue a seção 1
- [ ] Configuração extraída para `config/` (nenhum segredo/flag hardcoded)
- [ ] Models abstraem os dados (sem SQL fora de models/database)
- [ ] Views/Routes separadas e finas
- [ ] Controllers concentram o fluxo
- [ ] Error handling centralizado
- [ ] Entry point claro e documentado
- [ ] Aplicação inicia sem erros e todos os endpoints originais respondem (validation-guide.md)
