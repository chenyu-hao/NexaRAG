from __future__ import annotations

from pathlib import Path


class StableMemory:
    """Long-term stable memory stored as memory.md."""

    def __init__(self, root: str | Path, user_id: str):
        self.root = Path(root)
        self.user_id = user_id
        self.path = self.root / user_id / "memory.md"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> str:
        if not self.path.exists():
            return ""
        return self.path.read_text(encoding="utf-8")

    def write(self, content: str):
        self.path.write_text(content, encoding="utf-8")
