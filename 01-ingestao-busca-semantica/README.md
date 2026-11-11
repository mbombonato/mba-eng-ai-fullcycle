# Ingestão e Busca Semântica com LangChain e Postgres

Desafio do módulo **Introdução ao LangChain** (MBA Engenharia de Software com IA, Full Cycle). Enunciado completo em [ENUNCIADO.md](ENUNCIADO.md).

O projeto lê o `document.pdf`, grava os embeddings no PostgreSQL com pgVector e responde perguntas pelo terminal usando apenas o conteúdo do PDF.

## Pré-requisitos

- Python 3 (testado com 3.14)
- Docker e Docker Compose
- Uma API Key da OpenAI (https://platform.openai.com/api-keys) ou da Google (https://aistudio.google.com/apikey)

## Como rodar

1. Crie o ambiente virtual e instale as dependências:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Crie o `.env` e preencha a chave do provedor escolhido (`OPENAI_API_KEY` ou `GOOGLE_API_KEY`):

   ```bash
   cp .env.example .env
   ```

3. Suba o banco de dados:

   ```bash
   docker compose up -d
   ```

   O serviço `bootstrap_vector_ext` cria a extensão `vector` assim que o Postgres fica saudável.

4. Execute a ingestão do PDF:

   ```bash
   python3 src/ingest.py
   ```

5. Rode o chat:

   ```bash
   python3 src/chat.py
   ```

   Digite `sair` (ou `Ctrl+C`) para encerrar.

Para encerrar o banco:

```bash
docker compose down        # para os containers
docker compose down -v     # para e apaga o volume (remove os vetores ingeridos)
```

## Resultado esperado

Ingestão:

```
PDF 'document.pdf' dividido em 67 chunks (chunk_size=1000, overlap=150).
  67/67 chunks gravados
Ingestão concluída com sucesso.
```

A collection é recriada a cada execução, então rodar a ingestão de novo não duplica os dados.

Chat (formato do enunciado):

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

## Variáveis do `.env`

| Variável | Descrição | Padrão |
|---|---|---|
| `LLM_PROVIDER` | `openai` ou `gemini` | `openai` |
| `OPENAI_API_KEY` | Chave da OpenAI (obrigatória se `openai`) | vazio |
| `OPENAI_EMBEDDING_MODEL` / `OPENAI_LLM_MODEL` | Modelos da OpenAI | `text-embedding-3-small` / `gpt-5.4-nano` |
| `GOOGLE_API_KEY` | Chave da Google (obrigatória se `gemini`) | vazio |
| `GOOGLE_EMBEDDING_MODEL` / `GOOGLE_LLM_MODEL` | Modelos do Gemini | `models/gemini-embedding-001` / `gemini-3.5-flash-lite` |
| `POSTGRES_PORT` | Porta do host usada pelo docker-compose | `5432` |
| `DATABASE_URL` | Conexão SQLAlchemy/psycopg com o banco | `postgresql+psycopg://postgres:postgres@localhost:5432/rag` |
| `PG_VECTOR_COLLECTION_NAME` | Nome da collection no PGVector | `document_chunks` |
| `PDF_PATH` | Caminho do PDF (relativo à raiz do projeto) | `document.pdf` |

Limitações ao rodar:

- Porta 5432 ocupada: defina, por exemplo, `POSTGRES_PORT=55432` e ajuste a porta em `DATABASE_URL` para `55432`.
- Troca de modelo ou provedor de embeddings: a tabela é criada na primeira ingestão com a dimensão do modelo escolhido. Apague o volume (`docker compose down -v`) ou use outro `PG_VECTOR_COLLECTION_NAME` e refaça a ingestão.

## Modelos utilizados

O desafio não fixa modelos. Os padrões são modelos leves de cada provedor na data da entrega e podem ser trocados no `.env`.

| Provedor | Embeddings | LLM |
|---|---|---|
| OpenAI (`LLM_PROVIDER=openai`) | `text-embedding-3-small` (1536 dimensões) | `gpt-5.4-nano` |
| Gemini (`LLM_PROVIDER=gemini`) | `models/gemini-embedding-001` (3072 dimensões) | `gemini-3.5-flash-lite` |

## Onde está cada requisito

| Requisito do enunciado | Onde |
|---|---|
| Ingestão: chunks de 1000 caracteres com overlap de 150, embedding de cada chunk, gravação no pgVector (`langchain_postgres.PGVector`) | `src/ingest.py` |
| Busca: vetoriza a pergunta, busca os 10 mais relevantes (`similarity_search_with_score(query, k=10)`), monta o prompt do enunciado e chama a LLM | `src/search.py` |
| Chat no terminal, com respostas baseadas apenas no PDF | `src/chat.py` |
| PostgreSQL 17 + pgVector via Docker Compose | `docker-compose.yml` |

Estrutura do projeto:

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
├── ENUNCIADO.md          # Enunciado do desafio
└── README.md
```

## Testes

Os testes não precisam de chave de API: usam embeddings determinísticos e uma LLM fake. Conferem o tamanho máximo dos chunks (1000) e as constantes de split, trechos do prompt, o uso de `k=10` e, com o banco no ar, a ingestão e a busca no pgVector. Os testes de integração são pulados quando o banco não está acessível.

```bash
docker compose up -d
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rag \
  python3 -m unittest discover -s tests -v
```

Eles usam a collection `test_document_chunks` e a removem ao final.
