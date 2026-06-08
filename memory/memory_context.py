from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from memory.daily_memory import DailyMemory
from memory.stable_memory import StableMemory


class MemoryContextBuilder:
    """Builds prompt-ready memory from stable, today, and yesterday files."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def build(self, user_id: str, today: date | None = None) -> str:
        today = today or date.today()
        yesterday = today - timedelta(days=1)

        stable = StableMemory(self.root, user_id).read().strip()
        today_text = DailyMemory(self.root, user_id).read(today).strip()
        yesterday_text = DailyMemory(self.root, user_id).read(yesterday).strip()

        parts = []
        if stable:
            parts.append(f"【长期稳定记忆】\n{stable}")
        if yesterday_text:
            parts.append(f"【昨日记忆】\n{yesterday_text}")
        if today_text:
            parts.append(f"【今日记忆】\n{today_text}")
        return "\n\n".join(parts)
