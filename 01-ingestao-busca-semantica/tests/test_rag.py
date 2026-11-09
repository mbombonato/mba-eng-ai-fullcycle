"""Testes sem chave de API: usam embeddings e LLM fake.

Os testes de integração precisam do Postgres do docker-compose rodando e
de DATABASE_URL definido (são pulados caso o banco não esteja acessível).
Execute com: python -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from langchain_core.embeddings import DeterministicFakeEmbedding  # noqa: E402
from langchain_core.language_models import FakeListChatModel  # noqa: E402

import ingest  # noqa: E402
import search  # noqa: E402

ENUNCIADO_PROMPT_RULES = (
    '- Se a informação não estiver explicitamente no CONTEXTO, responda:\n'
    '  "Não tenho informações necessárias para responder sua pergunta."'
)


class FakeStore:
    def __init__(self, docs):
        self.docs = docs
        self.calls = []

    def similarity_search_with_score(self, query, k):
        self.calls.append((query, k))
        return [(d, 0.1) for d in self.docs[:k]]


class RecordingLLM(FakeListChatModel):
    prompts: list = []

    def _call(self, messages, *args, **kwargs):
        self.prompts.append(messages[-1].content)
        return super()._call(messages, *args, **kwargs)


class UnitTests(unittest.TestCase):
    def test_split_params(self):
        chunks = ingest.load_and_split(ROOT / "document.pdf")
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c.page_content) <= 1000 for c in chunks))
        self.assertEqual((ingest.CHUNK_SIZE, ingest.CHUNK_OVERLAP), (1000, 150))

    def test_prompt_template(self):
        self.assertIn(ENUNCIADO_PROMPT_RULES, search.PROMPT_TEMPLATE)
        self.assertIn('RESPONDA A "PERGUNTA DO USUÁRIO"', search.PROMPT_TEMPLATE)

    def test_chain_uses_k10_and_fills_prompt(self):
        from langchain_core.documents import Document

        docs = [Document(page_content=f"trecho {i}") for i in range(15)]
        store = FakeStore(docs)
        llm = RecordingLLM(responses=["resposta fake"], prompts=[])
        chain = search.build_chain(store, llm)

        self.assertEqual(chain.invoke("Qual o faturamento?"), "resposta fake")
        self.assertEqual(store.calls, [("Qual o faturamento?", 10)])
        sent = llm.prompts[0]
        self.assertIn("trecho 9", sent)
        self.assertNotIn("trecho 10", sent)
        self.assertIn("PERGUNTA DO USUÁRIO:\nQual o faturamento?", sent)

    def test_missing_key_returns_none(self):
        old = os.environ.pop("OPENAI_API_KEY", None)
        os.environ["LLM_PROVIDER"] = "openai"
        try:
            self.assertIsNone(search.search_prompt())
        finally:
            if old is not None:
                os.environ["OPENAI_API_KEY"] = old


def _db_available():
    if not os.getenv("DATABASE_URL"):
        return False
    try:
        import sqlalchemy

        with sqlalchemy.create_engine(os.environ["DATABASE_URL"]).connect():
            return True
    except Exception:
        return False


@unittest.skipUnless(_db_available(), "Postgres/pgvector indisponível")
class IntegrationTests(unittest.TestCase):
    def setUp(self):
        os.environ["PG_VECTOR_COLLECTION_NAME"] = "test_document_chunks"
        self.emb = DeterministicFakeEmbedding(size=64)

    def test_ingest_and_search(self):
        n = ingest.ingest_pdf(embeddings=self.emb)
        n2 = ingest.ingest_pdf(embeddings=self.emb)  # reingestão não duplica
        self.assertEqual(n, n2)

        store = search.get_vector_store(embeddings=self.emb)
        first_chunk = ingest.load_and_split(ingest.resolve_pdf_path())[0].page_content
        results = store.similarity_search_with_score(first_chunk, k=10)
        self.assertEqual(len(results), min(10, n))
        # Embedding determinístico: o próprio texto deve ser o mais próximo.
        self.assertEqual(results[0][0].page_content, first_chunk)

        llm = FakeListChatModel(responses=["ok"])
        self.assertEqual(search.build_chain(store, llm).invoke("pergunta"), "ok")

        store.delete_collection()


if __name__ == "__main__":
    unittest.main()
