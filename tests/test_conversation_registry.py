from core.conversation_repository import MemoryConversationRepository
from core.conversation_registry import ConversationRegistry


def test_conversation_registry_creates_and_reuses_conversation():
    registry = ConversationRegistry(repository=MemoryConversationRepository())

    first = registry.get_or_create(conversation_id="abc12345", user_id="user1")
    second = registry.get_or_create(conversation_id="abc12345", user_id="user1")

    assert first is second
    assert first.conversation_id == "abc12345"
    assert first.session_id == "abc12345"
    assert first.user_id == "user1"


def test_conversation_registry_lists_active_conversations():
    registry = ConversationRegistry(repository=MemoryConversationRepository())

    registry.get_or_create(conversation_id="s1", user_id="u1")
    registry.get_or_create(conversation_id="s2", user_id="u2")

    listed = registry.list_all()

    assert {item["session_id"] for item in listed} == {"s1", "s2"}
    assert {item["conversation_id"] for item in listed} == {"s1", "s2"}


def test_memory_conversation_repository_persists_index_records():
    repository = MemoryConversationRepository()

    repository.touch_conversation("s1", "u1")
    repository.touch_conversation("s2", "u2")

    listed = repository.list_conversations()

    assert [item["session_id"] for item in listed] == ["s1", "s2"]
    assert [item["conversation_id"] for item in listed] == ["s1", "s2"]
