"""Backward-compatible knowledge service wrapper."""

from rag.knowledge_base import KnowledgeBase


class KnowledgeService(KnowledgeBase):
    """Compatibility layer for older imports during the staged refactor."""

    def upload(self, text: str, filename: str) -> str:
        return self.add_document(text, filename)
