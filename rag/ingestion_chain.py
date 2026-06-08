from __future__ import annotations

from rag.ingestion import KnowledgeIngestion


class KnowledgeIngestionChain:
    """Knowledge-base storage chain: load, split, embed, and index documents."""

    def __init__(self, ingestion: KnowledgeIngestion | None = None):
        self.ingestion = ingestion or KnowledgeIngestion()

    def add_document(self, text: str, source: str) -> str:
        return self.ingestion.add_document(text, source)

    def add_file(self, path: str) -> str:
        return self.ingestion.add_file(path)
