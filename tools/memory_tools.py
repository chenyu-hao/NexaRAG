from __future__ import annotations

import json
from datetime import date as date_type
from pathlib import Path

from langchain_core.tools import StructuredTool

from memory.daily_memory import DailyMemory
from memory.memory_context import MemoryContextBuilder
from memory.stable_memory import StableMemory


class FileMemoryReader:
    def __init__(self, root, today: date_type | None = None):
        self.root = Path(root)
        self.today = today

    def read_stable_memory(self, user_id: str) -> str:
        return StableMemory(self.root, user_id).read()

    def read_daily_memory(self, user_id: str, date: str) -> str:
        return DailyMemory(self.root, user_id).read(date_type.fromisoformat(date))

    def search_session_log(self, user_id: str, query: str) -> str:
        sessions_dir = self.root / user_id / "sessions"
        if not sessions_dir.exists():
            return ""
        matches = []
        for path in sessions_dir.glob("*.jsonl"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if query in line:
                    try:
                        event = json.loads(line)
                        matches.append(event.get("content", line))
                    except json.JSONDecodeError:
                        matches.append(line)
        return "\n".join(matches)

    def get_memory_context(self, user_id: str) -> str:
        return MemoryContextBuilder(self.root).build(user_id, today=self.today)


def build_memory_tools(memory_reader) -> list:
    def read_stable_memory(user_id: str) -> str:
        """Read stable long-term memory for a user."""
        return memory_reader.read_stable_memory(user_id)

    def read_daily_memory(user_id: str, date: str) -> str:
        """Read daily memory for a user and date."""
        return memory_reader.read_daily_memory(user_id, date)

    def search_session_log(user_id: str, query: str) -> str:
        """Search a user's session logs."""
        return memory_reader.search_session_log(user_id, query)

    def get_memory_context(user_id: str) -> str:
        """Get prompt-ready memory context for a user."""
        return memory_reader.get_memory_context(user_id)

    return [
        StructuredTool.from_function(read_stable_memory),
        StructuredTool.from_function(read_daily_memory),
        StructuredTool.from_function(search_session_log),
        StructuredTool.from_function(get_memory_context),
    ]
