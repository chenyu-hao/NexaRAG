from __future__ import annotations

from rag.retriever import KnowledgeRetriever


class QuestionAnswerRetrievalChain:
    """Question-answer retrieval chain used by tools and Agent nodes."""

    def __init__(self, retriever: KnowledgeRetriever | None = None):
        self.retriever = retriever or KnowledgeRetriever()

    def search(self, query: str, top_k: int | None = None):
        return self.retriever.search(query, top_k=top_k)

    def search_product(self, product_name: str, top_k: int | None = None):
        return self.retriever.search_product(product_name, top_k=top_k)

    def search_troubleshoot(self, problem: str, top_k: int | None = None):
        return self.retriever.search_troubleshoot(problem, top_k=top_k)

    def search_as_documents(self, query: str, top_k: int | None = None):
        return self.retriever.search_as_documents(query, top_k=top_k)

    def sync_index(self) -> int:
        return self.retriever.sync_index()
