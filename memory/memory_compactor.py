from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass
class CompactConfig:
    enable_context_compaction: bool = True
    context_keep_head_turns: int = 2
    context_keep_tail_turns: int = 6
    tool_result_placeholder_max_chars: int = 200
    middle_summary_max_chars: int = 1200
    daily_memory_filename: str = "每日记忆.md"


@dataclass
class PlaceholderRecord:
    tool: str
    index: int
    chars: int
    position: int
    args_summary: str = ""
    omitted: bool = True


@dataclass
class CompactResult:
    compact_context: str
    daily_memory_written: bool = False
    placeholder_index: list[PlaceholderRecord] = field(default_factory=list)
    summary_status: str = "none"
    fallback_used: bool = False
    errors: list[str] = field(default_factory=list)


class MemoryCompactor:
    """Build compact prompt-ready context from a conversation."""

    def compact(
        self,
        messages: list[Any],
        session_id: str,
        user_id: str,
        summary: str = "",
        config: CompactConfig | dict[str, Any] | None = None,
        llm: Any | None = None,
        memory_root: str | Path | None = None,
    ) -> CompactResult:
        del session_id, user_id, memory_root
        compact_config = self._coerce_config(config)
        normalized = [self._normalize_message(message) for message in messages]
        if not normalized:
            return CompactResult(compact_context="")

        if not compact_config.enable_context_compaction:
            return CompactResult(compact_context=self._render_original(normalized, summary))

        compacted_messages, placeholders = self._replace_large_tool_results(
            normalized,
            threshold=compact_config.tool_result_placeholder_max_chars,
        )
        turns = self._group_turns(compacted_messages)
        if len(turns) <= compact_config.context_keep_head_turns + compact_config.context_keep_tail_turns:
            context = self._render_sections(
                head_turns=turns,
                middle_summary="",
                tail_turns=[],
                placeholders=placeholders,
            )
            return CompactResult(compact_context=context, placeholder_index=placeholders)

        head_count = max(compact_config.context_keep_head_turns, 0)
        tail_count = max(compact_config.context_keep_tail_turns, 0)
        head_indexes = set(range(min(head_count, len(turns))))
        tail_start = max(len(turns) - tail_count, 0)
        tail_indexes = set(range(tail_start, len(turns))) if tail_count else set()
        keep_indexes = head_indexes | tail_indexes
        middle_turns = [turn for index, turn in enumerate(turns) if index not in keep_indexes]
        head_turns = [turn for index, turn in enumerate(turns) if index in head_indexes]
        tail_turns = [turn for index, turn in enumerate(turns) if index in tail_indexes and index not in head_indexes]
        middle_summary, status, fallback_used, errors = self._summarize_middle(
            middle_turns=middle_turns,
            config=compact_config,
            llm=llm,
        )
        context = self._render_sections(
            head_turns=head_turns,
            middle_summary=middle_summary,
            tail_turns=tail_turns,
            placeholders=placeholders,
        )
        return CompactResult(
            compact_context=context,
            placeholder_index=placeholders,
            summary_status=status,
            fallback_used=fallback_used,
            errors=errors,
        )

    def compact_session(self, messages: list[dict]) -> str:
        return self.compact(
            messages=messages,
            session_id="",
            user_id="",
            summary="",
            config=CompactConfig(),
        ).compact_context

    @staticmethod
    def _coerce_config(config: CompactConfig | dict[str, Any] | None) -> CompactConfig:
        if isinstance(config, CompactConfig):
            return config
        if isinstance(config, dict):
            valid = {field.name for field in CompactConfig.__dataclass_fields__.values()}
            return CompactConfig(**{key: value for key, value in config.items() if key in valid})
        return CompactConfig()

    @staticmethod
    def _normalize_message(message: Any) -> dict[str, Any]:
        if isinstance(message, dict):
            role = message.get("role") or message.get("type") or "unknown"
            content = message.get("content", "")
            return {**message, "role": role, "content": "" if content is None else str(content)}
        role = getattr(message, "role", getattr(message, "type", "unknown"))
        content = getattr(message, "content", "")
        image_count = getattr(message, "image_count", 0)
        return {"role": role, "content": "" if content is None else str(content), "image_count": image_count}

    @staticmethod
    def _group_turns(messages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        turns: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []
        for message in messages:
            if message.get("role") == "user" and current:
                turns.append(current)
                current = []
            current.append(message)
        if current:
            turns.append(current)
        return turns

    def _render_original(self, messages: list[dict[str, Any]], summary: str = "") -> str:
        parts = []
        if summary:
            parts.append(f"【历史摘要】\n{summary}")
        if messages:
            parts.append("【最近对话】")
            parts.extend(self._render_messages(messages))
        return "\n".join(parts)

    def _render_sections(
        self,
        head_turns: list[list[dict[str, Any]]],
        middle_summary: str,
        tail_turns: list[list[dict[str, Any]]],
        placeholders: list[PlaceholderRecord] | None = None,
    ) -> str:
        parts: list[str] = []
        if head_turns:
            parts.append("【会话起始保留】")
            parts.extend(self._render_messages([message for turn in head_turns for message in turn]))
        if middle_summary:
            parts.append(middle_summary)
        if tail_turns:
            parts.append("【近期对话保留】")
            parts.extend(self._render_messages([message for turn in tail_turns for message in turn]))
        if placeholders:
            parts.append("【工具结果占位符索引】")
            parts.extend(
                f"- index={record.index}, tool={record.tool}, chars={record.chars}, "
                f"position={record.position}, args={record.args_summary or '无'}, omitted={record.omitted}"
                for record in placeholders
            )
        return "\n".join(parts)

    @staticmethod
    def _render_messages(messages: list[dict[str, Any]]) -> list[str]:
        labels = {
            "user": "用户",
            "assistant": "助手",
            "tool": "工具",
            "system": "系统",
        }
        rendered = []
        for message in messages:
            role = str(message.get("role", "unknown"))
            label = labels.get(role, role)
            image_count = message.get("image_count", 0)
            extra = f"[附图{image_count}张] " if image_count else ""
            rendered.append(f"{label}: {extra}{message.get('content', '')}")
        return rendered

    def _replace_large_tool_results(
        self,
        messages: list[dict[str, Any]],
        threshold: int,
    ) -> tuple[list[dict[str, Any]], list[PlaceholderRecord]]:
        result = []
        placeholders: list[PlaceholderRecord] = []
        for position, message in enumerate(messages):
            copied = dict(message)
            field_name = self._large_tool_result_field(copied, threshold)
            if field_name:
                original = str(copied.get(field_name, ""))
                index = len(placeholders) + 1
                tool = self._tool_name(copied)
                placeholder = (
                    f"[TOOL_RESULT_PLACEHOLDER: tool={tool}, index={index}, chars={len(original)}]"
                )
                copied[field_name] = placeholder
                if field_name != "content":
                    copied["content"] = placeholder
                placeholders.append(
                    PlaceholderRecord(
                        tool=tool,
                        index=index,
                        chars=len(original),
                        position=position,
                        args_summary=self._args_summary(copied),
                        omitted=True,
                    )
                )
            result.append(copied)
        return result, placeholders

    @staticmethod
    def _large_tool_result_field(message: dict[str, Any], threshold: int) -> str:
        role = str(message.get("role", ""))
        event_type = str(message.get("type", ""))
        if role == "tool" and len(str(message.get("content", ""))) > threshold:
            return "content"
        if event_type == "node_finished" or role in {"node", "tool_result"}:
            for field_name in ("result", "context", "content"):
                if len(str(message.get(field_name, ""))) > threshold:
                    return field_name
        return ""

    @staticmethod
    def _tool_name(message: dict[str, Any]) -> str:
        return str(
            message.get("name")
            or message.get("tool")
            or message.get("node")
            or message.get("type")
            or "unknown"
        )

    @staticmethod
    def _args_summary(message: dict[str, Any]) -> str:
        args = message.get("args") or message.get("arguments") or message.get("metadata") or ""
        if not args:
            return ""
        try:
            text = json.dumps(args, ensure_ascii=False, sort_keys=True)
        except TypeError:
            text = str(args)
        return text[:160]

    def _summarize_middle(
        self,
        middle_turns: list[list[dict[str, Any]]],
        config: CompactConfig,
        llm: Any | None,
    ) -> tuple[str, str, bool, list[str]]:
        if not middle_turns:
            return "", "none", False, []
        middle_text = "\n".join(self._render_messages([message for turn in middle_turns for message in turn]))
        if llm is not None:
            try:
                prompt = self._build_summary_prompt(middle_text, config.middle_summary_max_chars)
                response = llm.invoke(prompt)
                content = getattr(response, "content", response)
                summary = str(content).strip()
                if summary:
                    return self._trim_summary(summary, config.middle_summary_max_chars), "llm", False, []
            except Exception as exc:
                return self._fallback_middle_summary(middle_turns), "fallback", True, [str(exc)]
        return self._fallback_middle_summary(middle_turns), "fallback", True, []

    @staticmethod
    def _build_summary_prompt(middle_text: str, max_chars: int) -> str:
        return (
            "请只根据以下中间会话内容生成任务列表摘要，不编造，不复述大段工具结果全文。"
            f"摘要不超过 {max_chars} 字，格式必须包含已完成、未完成、失败/阻塞、"
            "重要事实/用户偏好、后续建议。\n\n"
            f"{middle_text}"
        )

    @staticmethod
    def _trim_summary(summary: str, max_chars: int) -> str:
        return summary if len(summary) <= max_chars else summary[:max_chars].rstrip()

    def _fallback_middle_summary(self, middle_turns: list[list[dict[str, Any]]]) -> str:
        messages = [message for turn in middle_turns for message in turn]
        user_messages = [m.get("content", "") for m in messages if m.get("role") == "user" and m.get("content")]
        assistant_count = sum(1 for m in messages if m.get("role") == "assistant")
        failures = [
            str(m.get("content") or m.get("summary") or m.get("type"))
            for m in messages
            if any(marker in str(m.get("type", "")) for marker in ("fail", "error", "失败", "错误", "阻塞"))
        ]
        return "\n".join([
            "【中间任务摘要】",
            "已完成：",
            f"- 中间历史包含 {assistant_count} 条助手响应，具体完成状态需结合近期上下文确认",
            "",
            "未完成：",
            *[f"- {content}" for content in user_messages],
            "",
            "失败/阻塞：",
            *(f"- {failure}" for failure in (failures or ["暂无明确失败或阻塞"])),
            "",
            "重要事实/用户偏好：",
            "- LLM 摘要不可用，使用规则摘要",
            "",
            "后续建议：",
            "- 继续处理近期对话中保留的最新请求",
        ])
