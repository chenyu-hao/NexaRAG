from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from memory.conversation import ConversationMemory


def now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class ConversationState:
    conversation_id: str
    user_id: str
    memory: ConversationMemory = field(default_factory=ConversationMemory)
    created_at: str = field(default_factory=now_string)
    last_active: str = field(default_factory=now_string)

    @property
    def session_id(self) -> str:
        return self.conversation_id
