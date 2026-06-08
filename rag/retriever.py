from __future__ import annotations

import logging

from config import settings as config
from rag.bm25 import BM25Retriever
from rag.embedding import EmbeddingService
from rag.vector import HybridRetriever, VectorRetriever

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """Coordinates vector, BM25, and hybrid knowledge retrieval."""

    def __init__(self, embedding=None, vector=None, bm25=None, hybrid=None):
        self.embedding = embedding or EmbeddingService()
        self.bm25 = bm25 or BM25Retriever()
        self.vector = vector or VectorRetriever(self.embedding)
        self.hybrid = hybrid or HybridRetriever(self.vector, self.bm25)

    def search(self, query: str, top_k: int | None = None):
        return self.hybrid.search(query, top_k=top_k)

    def search_as_documents(self, query: str, top_k: int | None = None):
        return self.hybrid.search_as_documents(query, top_k=top_k)

    def search_product(self, product_name: str, top_k: int | None = None):
        return self.search(product_name, top_k=top_k or 6)

    def search_troubleshoot(self, problem: str, top_k: int | None = None):
        return self.search(problem, top_k=top_k or 8)

    def sync_index(self) -> int:
        try:
            collection = self.vector.store._collection
            offset = 0
            batch_size = 500
            total = 0
            while True:
                data = collection.get(
                    include=["documents", "metadatas"],
                    limit=batch_size,
                    offset=offset,
                )
                if not data["documents"]:
                    break
                if offset == 0:
                    self.bm25.clear()
                self.bm25.add_documents(data["documents"], data["metadatas"])
                total += len(data["documents"])
                offset += batch_size
            logger.info("Knowledge index synced: %d docs", total)
            return total
        except Exception as e:
            logger.error("Knowledge index sync failed: %s", e)
            return 0
