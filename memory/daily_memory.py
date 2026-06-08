from __future__ import annotations

from datetime import date
from pathlib import Path


class DailyMemory:
    """Append-only daily Markdown memory."""

    def __init__(self, root: str | Path, user_id: str):
        self.root = Path(root)
        self.user_id = user_id

    def path_for(self, day: date | None = None) -> Path:
        day = day or date.today()
        path = self.root / self.user_id / "daily" / f"{day.isoformat()}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def summary_path(self, filename: str = "每日记忆.md") -> Path:
        path = self.root / self.user_id / "daily" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def append(self, block: str, day: date | None = None):
        path = self.path_for(day)
        with path.open("a", encoding="utf-8") as f:
            if path.stat().st_size > 0:
                f.write("\n\n")
            f.write(block.rstrip() + "\n")

    def append_summary(self, block: str, filename: str = "每日记忆.md"):
        path = self.summary_path(filename)
        with path.open("a", encoding="utf-8") as f:
            if path.stat().st_size > 0:
                f.write("\n\n")
            f.write(block.rstrip() + "\n")

    def read(self, day: date | None = None) -> str:
        path = self.path_for(day)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def read_summary(self, filename: str = "每日记忆.md") -> str:
        path = self.summary_path(filename)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")
