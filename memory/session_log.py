from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class SessionLog:
    """Append-only JSONL session log."""

    def __init__(self, root: str | Path, user_id: str, session_id: str):
        self.root = Path(root)
        self.user_id = user_id
        self.session_id = session_id
        self.path = self.root / user_id / "sessions" / f"{session_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: dict):
        payload = dict(event)
        payload.setdefault("timestamp", datetime.now().isoformat())
        payload.setdefault("user_id", self.user_id)
        payload.setdefault("session_id", self.session_id)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
