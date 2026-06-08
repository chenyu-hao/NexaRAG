from __future__ import annotations

from datetime import datetime


class MemoryConversationRepository:
    """In-memory conversation index repository."""

    def __init__(self):
        self._conversations: dict[str, dict] = {}

    def touch_conversation(self, conversation_id: str, user_id: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        created_at = self._conversations.get(conversation_id, {}).get("created_at", now)
        self._conversations[conversation_id] = {
            "conversation_id": conversation_id,
            "session_id": conversation_id,
            "user_id": user_id,
            "created_at": created_at,
            "last_active": now,
            "turn_count": self._conversations.get(conversation_id, {}).get("turn_count", 0),
        }

    def list_conversations(self) -> list[dict]:
        return list(self._conversations.values())

    def delete_conversation(self, conversation_id: str):
        self._conversations.pop(conversation_id, None)

    def save_message(self, session_id: str, role: str, content: str, image_count: int = 0):
        if session_id in self._conversations and role == "user":
            self._conversations[session_id]["turn_count"] += 1

    def get_messages(self, session_id: str) -> list[dict]:
        return []

    def save_summary(self, session_id: str, summary: str):
        pass

    def get_summary(self, session_id: str) -> str:
        return ""

    def touch_session(self, session_id: str, user_id: str):
        self.touch_conversation(session_id, user_id)

    def list_sessions(self) -> list[dict]:
        return self.list_conversations()

    def delete_session(self, session_id: str):
        self.delete_conversation(session_id)
