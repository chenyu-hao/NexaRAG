from __future__ import annotations

from rag.ingestion_chain import KnowledgeIngestionChain
from rag.retrieval_chain import QuestionAnswerRetrievalChain


class KnowledgeBase:
    """Unified entry point for knowledge ingestion and retrieval."""

    def __init__(self, ingestion=None, retriever=None,
                 ingestion_chain=None, retrieval_chain=None):
        self.ingestion_chain = ingestion_chain or KnowledgeIngestionChain(ingestion)
        self.retrieval_chain = retrieval_chain or QuestionAnswerRetrievalChain(retriever)
        self.ingestion = self.ingestion_chain.ingestion
        self.retriever = self.retrieval_chain.retriever

    def add_document(self, text: str, source: str) -> str:
        return self.ingestion_chain.add_document(text, source)

    def add_file(self, path: str) -> str:
        return self.ingestion_chain.add_file(path)

    def search(self, query: str, top_k: int | None = None):
        return self.retrieval_chain.search(query, top_k=top_k)

    def search_product(self, product_name: str, top_k: int | None = None):
        return self.retrieval_chain.search_product(product_name, top_k=top_k)

    def search_troubleshoot(self, problem: str, top_k: int | None = None):
        return self.retrieval_chain.search_troubleshoot(problem, top_k=top_k)

    def search_as_documents(self, query: str, top_k: int | None = None):
        return self.retrieval_chain.search_as_documents(query, top_k=top_k)

    def sync_index(self) -> int:
        return self.retrieval_chain.sync_index()
