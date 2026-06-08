from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from config import settings as config
from memory.daily_memory import DailyMemory
from memory.stable_memory import StableMemory


@dataclass
class DailySnapshotResult:
    written: bool
    date_filename: str
    summary_written: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class PromoteMemoryResult:
    promoted: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    memory_path: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def promoted_count(self) -> int:
        return len(self.promoted)


class MemoryService:
    """Memory-system orchestration for daily and stable memory."""

    daily_memory_cls = DailyMemory
    stable_memory_cls = StableMemory

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def record_daily_snapshot(
        self,
        user_id: str,
        session_id: str,
        messages: list[Any],
        events: list[dict[str, Any]] | None = None,
        reason: str = "chat_turn",
        day: date | None = None,
    ) -> DailySnapshotResult:
        day = day or date.today()
        block = self._build_daily_block(
            user_id=user_id,
            session_id=session_id,
            messages=messages,
            events=events or [],
            reason=reason,
        )
        errors: list[str] = []
        daily = self.daily_memory_cls(self.root, user_id)
        date_filename = f"{day.isoformat()}.md"
        written = False
        summary_written = False
        try:
            daily.append(block, day=day)
            written = True
        except Exception as exc:  # pragma: no cover - exact exception depends on filesystem
            errors.append(str(exc))
        if getattr(config, "write_daily_summary_file", True):
            try:
                daily.append_summary(block, filename=getattr(config, "daily_memory_filename", "每日记忆.md"))
                summary_written = True
            except Exception as exc:
                errors.append(str(exc))
        return DailySnapshotResult(
            written=written,
            date_filename=date_filename,
            summary_written=summary_written,
            errors=errors,
        )

    def promote_daily_to_stable(
        self,
        user_id: str,
        day: date | None = None,
        dry_run: bool = False,
    ) -> PromoteMemoryResult:
        daily = self.daily_memory_cls(self.root, user_id)
        stable = self.stable_memory_cls(self.root, user_id)
        result = PromoteMemoryResult(memory_path=str(stable.path))
        try:
            text = daily.read(day=day)
            candidates = self._extract_long_term_candidates(text)
            existing = stable.read()
            existing_lines = {self._normalize_memory_line(line) for line in existing.splitlines()}
            promoted = []
            for candidate in candidates:
                normalized = self._normalize_memory_line(candidate)
                if not normalized:
                    continue
                if normalized in existing_lines:
                    result.skipped.append(candidate)
                    continue
                promoted.append(candidate)
                existing_lines.add(normalized)
            result.promoted = promoted
            if promoted and not dry_run:
                next_content = self._merge_stable_memory(existing, promoted)
                stable.write(next_content)
        except Exception as exc:  # pragma: no cover - exact exception depends on filesystem
            result.errors.append(str(exc))
        return result

    def _build_daily_block(
        self,
        user_id: str,
        session_id: str,
        messages: list[Any],
        events: list[dict[str, Any]],
        reason: str,
    ) -> str:
        del user_id
        normalized_messages = [self._normalize_message(message) for message in messages]
        user_messages = [m["content"] for m in normalized_messages if m["role"] == "user" and m["content"]]
        assistant_count = sum(1 for m in normalized_messages if m["role"] == "assistant")
        action_lines = self._event_action_lines(events)
        candidates = self._candidate_lines(user_messages)
        lines = [
            f"## Session {session_id} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"- 触发来源：{reason}",
            "",
            "### 本轮/本次请求",
            *self._bullet_lines(user_messages or ["无用户请求"]),
            "",
            "### 执行动作",
            *self._bullet_lines(action_lines or [f"记录助手回复数量：{assistant_count}"]),
            "",
            "### 已完成",
            *self._bullet_lines([f"已记录会话快照，消息数：{len(normalized_messages)}"]),
            "",
            "### 未完成",
            "- 暂无明确未完成事项",
            "",
            "### 失败/阻塞",
            *self._bullet_lines(self._failure_lines(events) or ["暂无明确失败或阻塞"]),
            "",
            "### 重要事实",
            *self._bullet_lines(candidates or ["暂无明确重要事实"]),
            "",
            "### 长期记忆候选",
            *self._bullet_lines(candidates or ["暂无明确长期记忆候选"]),
        ]
        return "\n".join(lines)

    @staticmethod
    def _normalize_message(message: Any) -> dict[str, str]:
        if isinstance(message, dict):
            return {
                "role": str(message.get("role") or message.get("type") or "unknown"),
                "content": str(message.get("content") or ""),
            }
        return {
            "role": str(getattr(message, "role", "unknown")),
            "content": str(getattr(message, "content", "") or ""),
        }

    @staticmethod
    def _event_action_lines(events: list[dict[str, Any]]) -> list[str]:
        lines = []
        for event in events:
            event_type = event.get("type", "event")
            summary = event.get("summary") or event.get("content") or event.get("result") or ""
            summary_text = " ".join(str(summary).split())
            if summary_text:
                lines.append(f"{event_type}: {summary_text[:200]}")
            else:
                lines.append(str(event_type))
        return lines

    @staticmethod
    def _failure_lines(events: list[dict[str, Any]]) -> list[str]:
        failures = []
        for event in events:
            event_type = str(event.get("type", ""))
            if any(marker in event_type for marker in ("fail", "error", "blocked", "失败", "错误", "阻塞")):
                summary = event.get("summary") or event.get("content") or event_type
                failures.append(str(summary)[:200])
        return failures

    @staticmethod
    def _candidate_lines(user_messages: list[str]) -> list[str]:
        markers = ("记住", "偏好", "以后", "长期", "用户信息", "项目约束", "喜欢")
        candidates = []
        for message in user_messages:
            compact = " ".join(message.split())
            if any(marker in compact for marker in markers):
                candidates.append(compact[:200])
        return candidates

    @staticmethod
    def _bullet_lines(items: list[str]) -> list[str]:
        return [f"- {item}" for item in items]

    @classmethod
    def _extract_long_term_candidates(cls, daily_text: str) -> list[str]:
        candidates = []
        for raw_line in daily_text.splitlines():
            line = raw_line.strip()
            if not line.startswith("-"):
                continue
            value = line.lstrip("-").strip()
            if not value or value.startswith("暂无"):
                continue
            if cls._looks_long_term(value):
                candidates.append(cls._clean_candidate(value))
        return cls._dedupe_preserve_order(candidates)

    @staticmethod
    def _looks_long_term(value: str) -> bool:
        markers = ("记住", "偏好", "以后", "长期", "用户信息", "项目约束", "喜欢")
        return any(marker in value for marker in markers)

    @staticmethod
    def _clean_candidate(value: str) -> str:
        for prefix in ("以后记住", "请记住", "记住"):
            if value.startswith(prefix):
                return value[len(prefix):].strip(" ，。:：")
        return value.strip()

    @staticmethod
    def _normalize_memory_line(value: str) -> str:
        return value.lstrip("-").strip().strip("。")

    @classmethod
    def _dedupe_preserve_order(cls, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            normalized = cls._normalize_memory_line(value)
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(value)
        return result

    @staticmethod
    def _merge_stable_memory(existing: str, promoted: list[str]) -> str:
        base = existing.rstrip()
        if not base:
            base = "# Long-term Memory"
        additions = "\n".join(f"- {item}" for item in promoted)
        return f"{base}\n\n{additions}\n"
