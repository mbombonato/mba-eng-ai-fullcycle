# Ingestão e Busca Semântica com LangChain e Postgres

Desafio do módulo **Introdução ao LangChain** (MBA Engenharia de Software com IA — Full Cycle).

Este software:

- **Ingestão** (`src/ingest.py`): lê o `document.pdf`, divide o texto em chunks de **1000 caracteres com overlap de 150**, gera o embedding de cada chunk e grava os vetores no **PostgreSQL + pgVector** (via `langchain_postgres.PGVector`).
- **Busca** (`src/search.py`): vetoriza a pergunta, busca os **10 chunks mais relevantes** (`similarity_search_with_score(query, k=10)`), monta o prompt definido no enunciado e chama a LLM.
- **Chat** (`src/chat.py`): CLI que recebe perguntas no terminal e responde **apenas** com base no conteúdo do PDF.

## Tecnologias

- Python 3.11+ (testado com Python 3.14)
- LangChain (`langchain-openai`, `langchain-google-genai`, `langchain-postgres`, `langchain-text-splitters`, `langchain-community`)
- PostgreSQL 17 + pgVector (Docker Compose)
- Provedor de modelos: **OpenAI** (padrão) ou **Gemini**

## Modelos utilizados

O desafio não fixa modelos. Os padrões são os modelos leves/baratos disponíveis atualmente, e todos podem ser trocados no `.env`:

| Provedor | Embeddings | LLM |
|---|---|---|
| OpenAI (`LLM_PROVIDER=openai`) | `text-embedding-3-small` (1536 dimensões) | `gpt-5.4-nano` |
| Gemini (`LLM_PROVIDER=gemini`) | `models/gemini-embedding-001` (3072 dimensões) | `gemini-3.5-flash-lite` |

> **Atenção à dimensão dos vetores:** a tabela é criada na primeira ingestão com a dimensão do modelo de embeddings escolhido. Se trocar de modelo/provedor de embeddings, apague o volume do banco (`docker compose down -v`) ou use outro `PG_VECTOR_COLLECTION_NAME`, e refaça a ingestão.

## Estrutura

```
├── docker-compose.yml    # Postgres + pgVector
├── requirements.txt      # Dependências
├── .env.example          # Template das variáveis de ambiente
├── src/
│   ├── ingest.py         # Script de ingestão do PDF
│   ├── search.py         # Busca vetorial + prompt + LLM
│   ├── chat.py           # CLI para interação com o usuário
├── tests/test_rag.py     # Testes (sem chave de API: embeddings/LLM fake)
├── document.pdf          # PDF para ingestão
└── README.md
```

## Pré-requisitos

- Python 3.11 ou superior
- Docker e Docker Compose
- Uma API Key da **OpenAI** (https://platform.openai.com/api-keys) **ou** da **Google** (https://aistudio.google.com/apikey)

## Configuração

1. Crie e ative o ambiente virtual e instale as dependências:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Crie o arquivo `.env` a partir do template e preencha a sua chave:

   ```bash
   cp .env.example .env
   ```

   | Variável | Descrição | Padrão |
   |---|---|---|
   | `LLM_PROVIDER` | `openai` ou `gemini` | `openai` |
   | `OPENAI_API_KEY` | Chave da OpenAI (obrigatória se `openai`) | — |
   | `OPENAI_EMBEDDING_MODEL` / `OPENAI_LLM_MODEL` | Modelos da OpenAI | `text-embedding-3-small` / `gpt-5.4-nano` |
   | `GOOGLE_API_KEY` | Chave da Google (obrigatória se `gemini`) | — |
   | `GOOGLE_EMBEDDING_MODEL` / `GOOGLE_LLM_MODEL` | Modelos do Gemini | `models/gemini-embedding-001` / `gemini-3.5-flash-lite` |
   | `POSTGRES_PORT` | Porta do host usada pelo docker-compose | `5432` |
   | `DATABASE_URL` | Conexão SQLAlchemy/psycopg com o banco | `postgresql+psycopg://postgres:postgres@localhost:5432/rag` |
   | `PG_VECTOR_COLLECTION_NAME` | Nome da collection no PGVector | `document_chunks` |
   | `PDF_PATH` | Caminho do PDF (relativo à raiz do projeto) | `document.pdf` |

   > Se a porta 5432 já estiver em uso na sua máquina, defina por exemplo `POSTGRES_PORT=55432` e ajuste a porta em `DATABASE_URL` para `55432`.

## Ordem de execução

1. Subir o banco de dados:

   ```bash
   docker compose up -d
   ```

   O serviço `bootstrap_vector_ext` cria a extensão `vector` assim que o Postgres fica saudável.

2. Executar a ingestão do PDF:

   ```bash
   python src/ingest.py
   ```

   Saída esperada:

   ```
   PDF 'document.pdf' dividido em 67 chunks (chunk_size=1000, overlap=150).
     67/67 chunks gravados
   Ingestão concluída com sucesso.
   ```

   A collection é recriada a cada execução, então rodar a ingestão de novo não duplica os dados.

3. Rodar o chat:

   ```bash
   python src/chat.py
   ```

   Digite `sair` (ou `Ctrl+C`) para encerrar.

## Exemplo de uso

```
Chat iniciado. Digite 'sair' (ou Ctrl+C) para encerrar.
Faça sua pergunta:

PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: O faturamento foi de 10 milhões de reais.

---

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.

---

PERGUNTA: sair
Até logo!
```

## Testes

Os testes não precisam de chave de API: usam embeddings determinísticos e uma LLM fake. Eles conferem o split (1000/150), o prompt, o uso de `k=10` e o fluxo completo de ingestão e busca no pgVector. Os testes de integração são pulados quando o banco não está acessível.

```bash
docker compose up -d
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rag \
  python -m unittest discover -s tests -v
```

Os testes usam a collection `test_document_chunks` e a removem ao final.

## Encerrando

```bash
docker compose down        # para os containers
docker compose down -v     # para e apaga o volume (remove os vetores ingeridos)
```
