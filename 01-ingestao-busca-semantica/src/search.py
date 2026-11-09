import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PROMPT_TEMPLATE = """
CONTEXTO:
{contexto}

REGRAS:
- Responda somente com base no CONTEXTO.
- Se a informação não estiver explicitamente no CONTEXTO, responda:
  "Não tenho informações necessárias para responder sua pergunta."
- Nunca invente ou use conhecimento externo.
- Nunca produza opiniões ou interpretações além do que está escrito.

EXEMPLOS DE PERGUNTAS FORA DO CONTEXTO:
Pergunta: "Qual é a capital da França?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Quantos clientes temos em 2024?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Você acha isso bom ou ruim?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

PERGUNTA DO USUÁRIO:
{pergunta}

RESPONDA A "PERGUNTA DO USUÁRIO"
"""

TOP_K = 10
DEFAULT_COLLECTION_NAME = "document_chunks"


class ConfigError(RuntimeError):
    """Erro de configuração (variável de ambiente ausente ou inválida)."""


def get_provider() -> str:
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider not in ("openai", "gemini"):
        raise ConfigError(f"LLM_PROVIDER inválido: '{provider}'. Use 'openai' ou 'gemini'.")
    return provider


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"A variável de ambiente {name} não está definida. Confira o arquivo .env.")
    return value


def get_embeddings():
    """Retorna o modelo de embeddings do provedor configurado."""
    if get_provider() == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001"),
            google_api_key=_require_env("GOOGLE_API_KEY"),
        )

    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        api_key=_require_env("OPENAI_API_KEY"),
    )


def get_llm():
    """Retorna o modelo de chat (LLM) do provedor configurado."""
    if get_provider() == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_LLM_MODEL", "gemini-3.5-flash-lite"),
            google_api_key=_require_env("GOOGLE_API_KEY"),
            temperature=0,
        )

    from langchain_openai import ChatOpenAI

    # Modelos da família GPT-5 não aceitam temperature diferente do padrão,
    # por isso o parâmetro não é enviado.
    return ChatOpenAI(
        model=os.getenv("OPENAI_LLM_MODEL", "gpt-5.4-nano"),
        api_key=_require_env("OPENAI_API_KEY"),
    )


def get_vector_store(embeddings=None, pre_delete_collection: bool = False):
    """Conecta ao PGVector (Postgres + pgvector) usando DATABASE_URL."""
    from langchain_postgres import PGVector

    return PGVector(
        embeddings=embeddings if embeddings is not None else get_embeddings(),
        connection=_require_env("DATABASE_URL"),
        collection_name=os.getenv("PG_VECTOR_COLLECTION_NAME") or DEFAULT_COLLECTION_NAME,
        use_jsonb=True,
        pre_delete_collection=pre_delete_collection,
    )


def format_context(results) -> str:
    """Concatena o conteúdo dos chunks retornados por similarity_search_with_score."""
    return "\n\n".join(doc.page_content.strip() for doc, _score in results)


def build_chain(vector_store, llm, k: int = TOP_K):
    """Monta a chain: pergunta -> busca vetorial (k) -> prompt -> LLM -> texto."""
    prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)

    def retrieve_context(question: str) -> str:
        # A pergunta é vetorizada pelo próprio vector store antes da busca.
        results = vector_store.similarity_search_with_score(question, k=k)
        return format_context(results)

    return (
        {"contexto": RunnableLambda(retrieve_context), "pergunta": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )


def search_prompt(question=None):
    """Inicializa a chain de busca + resposta.

    - Sem argumento: retorna a chain (use ``chain.invoke(pergunta)``), ou ``None``
      se a inicialização falhar.
    - Com ``question``: já executa a chain e retorna a resposta em texto.
    """
    try:
        chain = build_chain(get_vector_store(), get_llm())
    except ConfigError as exc:
        print(f"Erro de configuração: {exc}")
        return None
    except Exception as exc:  # falha de conexão com o banco, pacote ausente etc.
        print(f"Erro ao inicializar a busca: {exc}")
        return None

    if question is not None:
        return chain.invoke(question)
    return chain
