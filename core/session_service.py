"""Backward-compatible session names for the conversation registry."""

from core.conversation_registry import ConversationRegistry
from core.conversation_state import ConversationState

Session = ConversationState
SessionManager = ConversationRegistry
