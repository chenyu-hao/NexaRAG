from __future__ import annotations

from memory.session_log import SessionLog


class SessionRecorder:
    """Records session events to append-only JSONL."""

    def __init__(self, root, user_id: str, session_id: str):
        self.log = SessionLog(root=root, user_id=user_id, session_id=session_id)

    def record(self, event: dict):
        self.log.append(event)
