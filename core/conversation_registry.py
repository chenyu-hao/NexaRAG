from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

from config import settings as config
from core.conversation_repository import MemoryConversationRepository
from core.conversation_state import ConversationState
from memory.conversation import ConversationMemory, Message

logger = logging.getLogger(__name__)


class ConversationRegistry:
    """Runtime registry for active conversations."""

    def __init__(self, llm=None, repository=None, store=None):
        self.conversations: dict[str, ConversationState] = {}
        self.sessions = self.conversations
        self.timeout = timedelta(hours=config.session_timeout_hours)
        self._llm = llm
        self.repository = repository or store or MemoryConversationRepository()
        self.store = self.repository

    def _make_on_message(self, conversation_id: str):
        repository = self.repository

        def on_message(role: str, content: str, image_count: int = 0):
            try:
                repository.save_message(conversation_id, role, content, image_count)
            except Exception as e:
                logger.error("Persist conversation message failed: %s", e)

        def on_summary(summary: str):
            try:
                repository.save_summary(conversation_id, summary)
            except Exception as e:
                logger.error("Persist conversation summary failed: %s", e)

        return on_message, on_summary

    def _touch(self, conversation_id: str, user_id: str):
        if hasattr(self.repository, "touch_conversation"):
            self.repository.touch_conversation(conversation_id, user_id)
        else:
            self.repository.touch_session(conversation_id, user_id)

    def _delete(self, conversation_id: str):
        if hasattr(self.repository, "delete_conversation"):
            self.repository.delete_conversation(conversation_id)
        else:
            self.repository.delete_session(conversation_id)

    def _list(self) -> list[dict]:
        if hasattr(self.repository, "list_conversations"):
            return self.repository.list_conversations()
        return self.repository.list_sessions()

    def _create_conversation(self, conversation_id: str, user_id: str) -> ConversationState:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        on_msg, on_sum = self._make_on_message(conversation_id)
        state = ConversationState(
            conversation_id=conversation_id,
            user_id=user_id,
            memory=ConversationMemory(
                llm=self._llm,
                on_message=on_msg,
                on_summary=on_sum,
            ),
            created_at=now,
            last_active=now,
        )
        self.conversations[conversation_id] = state
        try:
            self._touch(conversation_id, user_id)
        except Exception as e:
            logger.error("Persist conversation failed: %s", e)
        return state

    def _restore_conversation(self, conversation_id: str, user_id: str) -> ConversationState | None:
        messages = self.repository.get_messages(conversation_id)
        if not messages:
            return None

        on_msg, on_sum = self._make_on_message(conversation_id)
        state = ConversationState(
            conversation_id=conversation_id,
            user_id=user_id,
            memory=ConversationMemory(
                llm=self._llm,
                on_message=on_msg,
                on_summary=on_sum,
            ),
        )
        for message in messages:
            state.memory.messages.append(Message(
                role=message["role"],
                content=message["content"],
                image_count=message.get("image_count", 0),
                timestamp=message.get("timestamp", ""),
            ))
        if hasattr(self.repository, "get_summary"):
            summary = self.repository.get_summary(conversation_id)
            if summary:
                state.memory.summary = summary

        state.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conversations[conversation_id] = state
        return state

    def get(self, conversation_id: str = None, user_id: str = "default",
            session_id: str = None) -> ConversationState | None:
        cid = conversation_id or session_id
        if cid in self.conversations:
            return self.conversations[cid]
        return self._restore_conversation(cid, user_id) if cid else None

    def get_or_create(self, conversation_id: str = None, user_id: str = "default",
                      session_id: str = None) -> ConversationState:
        cid = conversation_id or session_id
        if cid and cid in self.conversations:
            state = self.conversations[cid]
            last = datetime.strptime(state.last_active, "%Y-%m-%d %H:%M:%S")
            if datetime.now() - last > self.timeout:
                self.remove(cid)
            else:
                state.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return state

        if cid:
            restored = self._restore_conversation(cid, user_id)
            if restored:
                return restored

        return self._create_conversation(cid or str(uuid.uuid4())[:8], user_id)

    def remove(self, conversation_id: str):
        self.conversations.pop(conversation_id, None)
        try:
            self._delete(conversation_id)
        except Exception as e:
            logger.error("Delete conversation failed: %s", e)

    def list_all(self) -> list[dict]:
        try:
            stored = self._list()
            if stored:
                return stored
        except Exception as e:
            logger.error("List conversations failed: %s", e)
        return [
            {
                "conversation_id": state.conversation_id,
                "session_id": state.session_id,
                "user_id": state.user_id,
                "turn_count": state.memory.turn_count,
                "created_at": state.created_at,
            }
            for state in self.conversations.values()
        ]
