from __future__ import annotations

import json
from pathlib import Path

from agent.runtime import AgentRuntime
from agent.schemas import AgentInput, AgentOutput
from config import settings as config
from core.recorder import SessionRecorder
from memory.daily_memory import DailyMemory
from memory.memory_compactor import CompactConfig, MemoryCompactor
from memory.memory_context import MemoryContextBuilder
from memory.memory_service import MemoryService


class ChatService:
    """Application service for chat request orchestration."""

    def __init__(
        self,
        conversations,
        agent_group=None,
        session_ender=None,
        memory_root=None,
        memory_service=None,
        context_compactor=None,
    ):
        self.session_ender = session_ender
        self.conversations = conversations
        self.agent_group = agent_group
        self.memory_root = Path(memory_root or Path(config.DATA_DIR) / "memory")
        self.memory_context_builder = MemoryContextBuilder(self.memory_root)
        self.memory_service = memory_service or MemoryService(self.memory_root)
        self.context_compactor = context_compactor or MemoryCompactor()

    async def chat(self, question: str, session_id: str | None = None,
                   user_id: str = "default", images: list[str] | None = None) -> dict:
        conversation = self.conversations.get_or_create(
            session_id=session_id,
            user_id=user_id,
        )
        if self.agent_group is None:
            raise RuntimeError("ChatService requires an agent_group for chat")
        recorder = self._recorder(user_id, conversation.session_id)
        memory_context = self.memory_context_builder.build(user_id)
        image_count = len(images or [])
        recorder.record({
            "type": "user_message",
            "content": question,
            "image_count": image_count,
        })
        chat_history = self._build_agent_chat_history(
            conversation=conversation,
            user_id=user_id,
            question=question,
            image_count=image_count,
        )
        output = await self.agent_group.run(AgentInput(
            question=question,
            user_id=user_id,
            session_id=conversation.session_id,
            chat_history=chat_history,
            images=images or [],
            memory_context=memory_context,
        ), runtime=AgentRuntime(recorder=recorder))
        conversation.memory.add_message("user", question, image_count=image_count)
        conversation.memory.add_message("assistant", output.answer)
        recorder.record({"type": "assistant_message", "content": output.answer})
        recorder.record({"type": "verification_result", "verification": output.verification})
        return self._response_from_output(output, conversation)

    async def chat_stream(self, question: str, session_id: str | None = None,
                          user_id: str = "default", images: list[str] | None = None):
        conversation = self.conversations.get_or_create(
            session_id=session_id,
            user_id=user_id,
        )
        if self.agent_group is None:
            raise RuntimeError("ChatService requires an agent_group for chat_stream")
        recorder = self._recorder(user_id, conversation.session_id)
        memory_context = self.memory_context_builder.build(user_id)
        image_count = len(images or [])
        recorder.record({
            "type": "user_message",
            "content": question,
            "image_count": image_count,
        })
        chat_history = self._build_agent_chat_history(
            conversation=conversation,
            user_id=user_id,
            question=question,
            image_count=image_count,
        )
        agent_input = AgentInput(
            question=question,
            user_id=user_id,
            session_id=conversation.session_id,
            chat_history=chat_history,
            images=images or [],
            memory_context=memory_context,
        )
        if hasattr(self.agent_group, "stream"):
            chunks = []
            async for chunk in self.agent_group.stream(
                agent_input,
                runtime=AgentRuntime(recorder=recorder),
            ):
                chunks.append(chunk)
                yield chunk
            output = self.agent_group.last_output
            if output is None:
                output = AgentOutput(answer="".join(chunks))
        else:
            output = await self.agent_group.run(agent_input)
            if output.answer:
                yield output.answer
        conversation.memory.add_message("user", question, image_count=image_count)
        conversation.memory.add_message("assistant", output.answer)
        recorder.record({"type": "assistant_message", "content": output.answer})
        recorder.record({"type": "verification_result", "verification": output.verification})
        meta = json.dumps({
            "intent": output.intent,
            "verification": output.verification,
            "session_id": conversation.session_id,
            "turn_count": conversation.memory.turn_count,
            "image_desc": output.image_desc,
            "detected_products": output.detected_products,
        }, ensure_ascii=False)
        yield f"\n__CA_META__{meta}__CA_META_END__"

    async def end_session(self, session_id: str, user_id: str = "default") -> dict:
        conversation = self.conversations.get(session_id=session_id, user_id=user_id)
        if not conversation:
            return {"error": "not_found"}
        self._append_daily_summary(user_id, session_id, conversation.memory)
        if self.session_ender is not None:
            await self.session_ender.end_session(user_id, conversation.memory)
        self.conversations.remove(session_id)
        return {"msg": f"会话 {session_id} 已结束"}

    def get_history(self, session_id: str, user_id: str = "default",
                    limit: int = 0, offset: int = 0) -> dict | None:
        conversation = self.conversations.get(session_id=session_id, user_id=user_id)
        if not conversation:
            return None
        all_messages = self.conversations.store.get_messages(session_id)
        if limit > 0:
            all_messages = all_messages[offset:offset + limit]
        elif offset > 0:
            all_messages = all_messages[offset:]
        messages = [
            {
                "role": message["role"],
                "content": message["content"],
                "image_count": message.get("image_count", 0),
                "timestamp": message.get("timestamp", ""),
            }
            for message in all_messages
        ]
        return {
            "session_id": session_id,
            "messages": messages,
            "total": len(all_messages),
            "summary": conversation.memory.summary,
        }

    @staticmethod
    def _response_from_output(output: AgentOutput, conversation) -> dict:
        return {
            "answer": output.answer,
            "session_id": conversation.session_id,
            "turn_count": conversation.memory.turn_count,
            "intent": output.intent,
            "verification": output.verification,
            "image_desc": output.image_desc,
            "detected_products": output.detected_products,
        }

    def _recorder(self, user_id: str, session_id: str) -> SessionRecorder:
        return SessionRecorder(self.memory_root, user_id=user_id, session_id=session_id)

    def _append_daily_summary(self, user_id: str, session_id: str, memory):
        lines = [f"## Session {session_id}"]
        user_messages = [message.content for message in memory.messages if message.role == "user"]
        assistant_count = sum(1 for message in memory.messages if message.role == "assistant")
        lines.append(f"- turns: {len(user_messages)}")
        if user_messages:
            lines.append("- user questions:")
            for content in user_messages:
                compact = " ".join(content.split())
                lines.append(f"  - {compact[:160]}")
        if assistant_count:
            lines.append(f"- assistant response recorded: {assistant_count}")
        if memory.summary:
            lines.append(f"- rolling summary: {memory.summary[:200]}")
        DailyMemory(self.memory_root, user_id).append("\n".join(lines))

    def _build_agent_chat_history(self, conversation, user_id: str, question: str, image_count: int = 0) -> str:
        if not getattr(config, "enable_context_compaction", True):
            return conversation.memory.get_context_string()

        history_messages = self._memory_messages(conversation.memory)
        snapshot_messages = [
            *history_messages,
            {"role": "user", "content": question, "image_count": image_count},
        ]
        try:
            self.memory_service.record_daily_snapshot(
                user_id=user_id,
                session_id=conversation.session_id,
                messages=snapshot_messages,
                events=[],
                reason="before_agent_compaction",
            )
        except Exception:
            pass

        try:
            result = self.context_compactor.compact(
                messages=history_messages,
                session_id=conversation.session_id,
                user_id=user_id,
                summary=conversation.memory.summary,
                config=self._compact_config(),
            )
            return result.compact_context
        except Exception:
            return conversation.memory.get_context_string()

    @staticmethod
    def _memory_messages(memory) -> list[dict]:
        return [
            {
                "role": message.role,
                "content": message.content,
                "image_count": getattr(message, "image_count", 0),
            }
            for message in memory.messages
        ]

    @staticmethod
    def _compact_config() -> CompactConfig:
        return CompactConfig(
            enable_context_compaction=getattr(config, "enable_context_compaction", True),
            context_keep_head_turns=getattr(config, "context_keep_head_turns", 2),
            context_keep_tail_turns=getattr(config, "context_keep_tail_turns", 6),
            tool_result_placeholder_max_chars=getattr(config, "tool_result_placeholder_max_chars", 200),
            middle_summary_max_chars=getattr(config, "middle_summary_max_chars", 1200),
            daily_memory_filename=getattr(config, "daily_memory_filename", "每日记忆.md"),
        )
