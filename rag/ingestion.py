from __future__ import annotations

import hashlib
import os
from datetime import datetime

from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings as config
from rag.embedding import EmbeddingService


class KnowledgeIngestion:
    """Handles document loading, chunking, and vector index writes."""

    def __init__(self, embedding=None, store=None, splitter=None):
        self.embedding = embedding or EmbeddingService()
        os.makedirs(config.persist_directory, exist_ok=True)
        self.store = store or Chroma(
            collection_name=config.collection_name,
            embedding_function=self.embedding,
            persist_directory=config.persist_directory,
        )
        self.splitter = splitter or RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.separators,
        )

    def add_file(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return self.add_document(f.read(), os.path.basename(path))

    def add_document(self, text: str, source: str) -> str:
        if not text.strip():
            return "[failed] empty content"

        md5 = hashlib.md5(text.encode("utf-8")).hexdigest()
        if self._check_md5(md5):
            return "[skipped] content already exists"

        chunks = (
            self.splitter.split_text(text)
            if len(text) > config.max_split_char_number
            else [text]
        )
        metadatas = [
            {"source": source, "chunk_id": i, "time": datetime.now().isoformat()}
            for i in range(len(chunks))
        ]
        self.store.add_texts(texts=chunks, metadatas=metadatas)
        self._save_md5(md5)
        return f"[success] loaded {len(chunks)} chunks"

    def _check_md5(self, md5: str) -> bool:
        os.makedirs(os.path.dirname(config.md5_path), exist_ok=True)
        if not os.path.exists(config.md5_path):
            return False
        with open(config.md5_path, "r", encoding="utf-8") as f:
            return md5 in f.read()

    def _save_md5(self, md5: str):
        os.makedirs(os.path.dirname(config.md5_path), exist_ok=True)
        with open(config.md5_path, "a", encoding="utf-8") as f:
            f.write(md5 + "\n")
