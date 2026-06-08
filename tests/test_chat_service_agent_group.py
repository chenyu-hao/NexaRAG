import pytest
import json
import asyncio

from agent.schemas import AgentOutput
from core.chat_service import ChatService
from core.conversation_registry import ConversationRegistry
from core.conversation_repository import MemoryConversationRepository


class FakeAgentGroup:
    def __init__(self):
        self.inputs = []

    async def run(self, agent_input, runtime=None):
        self.inputs.append(agent_input)
        return AgentOutput(
            answer="group answer",
            intent={"intent": "product_query", "confidence": 0.9},
            verification={"pass": True},
            image_desc="image",
            detected_products=["phone"],
        )


class FakeSessionEnder:
    def __init__(self):
        self.ended = []

    async def end_session(self, user_id, memory):
        self.ended.append((user_id, memory.turn_count))


class FakeStreamingAgentGroup(FakeAgentGroup):
    async def stream(self, agent_input, runtime=None):
        self.inputs.append(agent_input)
        yield "group "
        yield "answer"
        self.last_output = AgentOutput(
            answer="group answer",
            intent={"intent": "product_query", "confidence": 0.9},
            verification={"pass": True},
        )


class FakeMemoryService:
    def __init__(self):
        self.snapshots = []

    def record_daily_snapshot(self, **kwargs):
        self.snapshots.append(kwargs)
        return type("DailyResult", (), {"written": True, "errors": []})()


class FakeCompactor:
    def __init__(self):
        self.calls = []

    def compact(self, **kwargs):
        self.calls.append(kwargs)
        return type("CompactResult", (), {
            "compact_context": "【会话起始保留】\n用户: old",
            "errors": [],
        })()


class NodeAnswer:
    async def run(self, state, runtime):
        return {
            "answer": "node answer",
            "verification": {"pass": True},
        }


@pytest.mark.asyncio
async def test_chat_service_uses_agent_group_and_updates_memory():
    conversations = ConversationRegistry(repository=MemoryConversationRepository())
    group = FakeAgentGroup()
    service = ChatService(conversations=conversations, agent_group=group)

    result = await service.chat("battery?", session_id="s1", user_id="u1", images=["img"])

    assert result["answer"] == "group answer"
    assert result["session_id"] == "s1"
    assert result["turn_count"] == 1
    assert result["intent"] == {"intent": "product_query", "confidence": 0.9}
    assert result["verification"] == {"pass": True}
    assert result["image_desc"] == "image"
    assert result["detected_products"] == ["phone"]

    conversation = conversations.get(session_id="s1", user_id="u1")
    assert [message.role for message in conversation.memory.messages] == ["user", "assistant"]
    assert conversation.memory.messages[0].content == "battery?"
    assert conversation.memory.messages[0].image_count == 1
    assert conversation.memory.messages[1].content == "group answer"

    assert group.inputs[0].question == "battery?"
    assert group.inputs[0].session_id == "s1"
    assert group.inputs[0].user_id == "u1"
    assert group.inputs[0].images == ["img"]


@pytest.mark.asyncio
async def test_chat_service_stream_uses_agent_group_and_emits_metadata():
    conversations = ConversationRegistry(repository=MemoryConversationRepository())
    group = FakeStreamingAgentGroup()
    service = ChatService(conversations=conversations, agent_group=group)

    chunks = []
    async for chunk in service.chat_stream("battery?", session_id="s1", user_id="u1"):
        chunks.append(chunk)

    raw = "".join(chunks)
    assert "group answer" in raw
    assert chunks[0:2] == ["group ", "answer"]
    assert "__CA_META__" in raw
    assert '"session_id": "s1"' in raw
    assert '"turn_count": 1' in raw

    conversation = conversations.get(session_id="s1", user_id="u1")
    assert [message.role for message in conversation.memory.messages] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_chat_service_records_session_log_and_injects_memory_context(tmp_path):
    conversations = ConversationRegistry(repository=MemoryConversationRepository())
    group = FakeAgentGroup()
    service = ChatService(
        conversations=conversations,
        agent_group=group,
        memory_root=tmp_path,
    )

    await service.chat("battery?", session_id="s1", user_id="u1")

    log_path = tmp_path / "u1" / "sessions" / "s1.jsonl"
    events = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]

    assert [event["type"] for event in events] == [
        "user_message",
        "assistant_message",
        "verification_result",
    ]
    assert group.inputs[0].memory_context == ""


@pytest.mark.asyncio
async def test_chat_service_passes_recorder_to_agent_group(tmp_path):
    from agent.groups.customer_service_group import CustomerServiceAgentGroup

    conversations = ConversationRegistry(repository=MemoryConversationRepository())
    group = CustomerServiceAgentGroup(nodes=[NodeAnswer()])
    service = ChatService(
        conversations=conversations,
        agent_group=group,
        memory_root=tmp_path,
    )

    await service.chat("battery?", session_id="s1", user_id="u1")

    log_path = tmp_path / "u1" / "sessions" / "s1.jsonl"
    event_types = [
        json.loads(line)["type"]
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]

    assert event_types == [
        "user_message",
        "node_started",
        "node_finished",
        "assistant_message",
        "verification_result",
    ]


@pytest.mark.asyncio
async def test_chat_service_appends_daily_memory_on_end_session(tmp_path):
    conversations = ConversationRegistry(repository=MemoryConversationRepository())
    session_ender = FakeSessionEnder()
    service = ChatService(
        conversations=conversations,
        agent_group=FakeAgentGroup(),
        session_ender=session_ender,
        memory_root=tmp_path,
    )

    await service.chat("battery?", session_id="s1", user_id="u1")
    result = await service.end_session("s1", user_id="u1")

    daily_files = list((tmp_path / "u1" / "daily").glob("*.md"))
    dated_daily_files = [
        path for path in daily_files
        if path.name != "每日记忆.md"
    ]
    assert result == {"msg": "会话 s1 已结束"}
    assert len(dated_daily_files) == 1
    assert (tmp_path / "u1" / "daily" / "每日记忆.md").exists()
    daily_text = dated_daily_files[0].read_text(encoding="utf-8")
    assert "Session s1" in daily_text
    assert "battery?" in daily_text
    assert "assistant response recorded" in daily_text
    assert "group answer" not in daily_text
    assert session_ender.ended == [("u1", 1)]


def test_chat_service_passes_compacted_chat_history_to_agent(tmp_path):
    conversations = ConversationRegistry(repository=MemoryConversationRepository())
    conversation = conversations.get_or_create(session_id="s1", user_id="u1")
    conversation.memory.add_message("user", "old")
    conversation.memory.add_message("assistant", "old answer")
    group = FakeAgentGroup()
    memory_service = FakeMemoryService()
    compactor = FakeCompactor()
    service = ChatService(
        conversations=conversations,
        agent_group=group,
        memory_root=tmp_path,
        memory_service=memory_service,
        context_compactor=compactor,
    )

    asyncio.run(service.chat("new", session_id="s1", user_id="u1"))

    assert group.inputs[0].chat_history == "【会话起始保留】\n用户: old"
    assert memory_service.snapshots[0]["reason"] == "before_agent_compaction"
    assert compactor.calls[0]["summary"] == conversation.memory.summary


def test_chat_service_uses_original_history_when_compaction_disabled(tmp_path, monkeypatch):
    from config import settings as config

    monkeypatch.setattr(config, "enable_context_compaction", False)
    conversations = ConversationRegistry(repository=MemoryConversationRepository())
    conversation = conversations.get_or_create(session_id="s1", user_id="u1")
    conversation.memory.add_message("user", "old")
    group = FakeAgentGroup()
    compactor = FakeCompactor()
    service = ChatService(
        conversations=conversations,
        agent_group=group,
        memory_root=tmp_path,
        context_compactor=compactor,
    )

    asyncio.run(service.chat("new", session_id="s1", user_id="u1"))

    assert "【最近对话】" in group.inputs[0].chat_history
    assert "用户: old" in group.inputs[0].chat_history
    assert compactor.calls == []
