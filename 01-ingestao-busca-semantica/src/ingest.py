import os
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv

# O enunciado recomenda o PyPDFLoader do langchain-community; o aviso de
# descontinuação do pacote não afeta o uso aqui.
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain_community")
warnings.filterwarnings("ignore", message=".*langchain-community.*")

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from search import ConfigError, get_vector_store

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

PDF_PATH = os.getenv("PDF_PATH")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
BATCH_SIZE = 100


def resolve_pdf_path(pdf_path=None) -> Path:
    path = Path(pdf_path or PDF_PATH or "document.pdf")
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def load_and_split(pdf_path) -> list:
    """Carrega o PDF e o divide em chunks de 1000 caracteres com overlap de 150."""
    docs = PyPDFLoader(str(pdf_path)).load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=False,
    )
    chunks = splitter.split_documents(docs)

    # Mantém só metadados úteis e não vazios (o PyPDFLoader traz vários campos do PDF).
    for chunk in chunks:
        chunk.metadata = {
            k: v for k, v in chunk.metadata.items()
            if k in ("source", "page", "page_label") and v not in (None, "")
        }
    return [c for c in chunks if c.page_content.strip()]


def ingest_pdf(pdf_path=None, embeddings=None) -> int:
    """Lê o PDF, gera os embeddings dos chunks e grava no PGVector.

    A collection é recriada a cada execução, então rodar a ingestão de novo
    não duplica os chunks.
    """
    path = resolve_pdf_path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {path}")

    chunks = load_and_split(path)
    if not chunks:
        raise ValueError(f"Nenhum texto extraído de {path}.")
    print(f"PDF '{path.name}' dividido em {len(chunks)} chunks "
          f"(chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}).")

    store = get_vector_store(embeddings=embeddings, pre_delete_collection=True)
    ids = [f"chunk-{i}" for i in range(len(chunks))]
    for start in range(0, len(chunks), BATCH_SIZE):
        end = start + BATCH_SIZE
        store.add_documents(chunks[start:end], ids=ids[start:end])
        print(f"  {min(end, len(chunks))}/{len(chunks)} chunks gravados")

    print("Ingestão concluída com sucesso.")
    return len(chunks)


if __name__ == "__main__":
    try:
        ingest_pdf()
    except (ConfigError, FileNotFoundError, ValueError) as exc:
        print(f"Erro: {exc}")
        sys.exit(1)
