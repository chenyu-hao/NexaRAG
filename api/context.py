from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import settings as config
from memory.memory_compactor import CompactConfig


router = APIRouter(prefix="/api/context", tags=["上下文"])


class CompactContextRequest(BaseModel):
    user_id: str = "default"
    session_id: str
    write_daily_snapshot: bool = True


def _messages_from_state(state) -> list[dict]:
    messages = []
    for message in state.memory.messages:
        if isinstance(message, dict):
            messages.append(message)
        else:
            messages.append({
                "role": getattr(message, "role", "unknown"),
                "content": getattr(message, "content", ""),
                "image_count": getattr(message, "image_count", 0),
            })
    return messages


@router.post("/compact")
async def compact_context(req: CompactContextRequest, request: Request):
    sessions = request.app.state.sessions
    state = sessions.get(session_id=req.session_id, user_id=req.user_id)
    if state is None:
        raise HTTPException(404, "会话不存在")

    messages = _messages_from_state(state)
    errors: list[str] = []
    daily_snapshot_written = False
    if req.write_daily_snapshot:
        daily_result = request.app.state.memory_service.record_daily_snapshot(
            user_id=req.user_id,
            session_id=req.session_id,
            messages=messages,
            events=[],
            reason="context_compaction",
        )
        daily_snapshot_written = bool(getattr(daily_result, "written", False))
        errors.extend(getattr(daily_result, "errors", []))

    compactor = request.app.state.context_compactor
    compact_result = compactor.compact(
        messages=messages,
        session_id=req.session_id,
        user_id=req.user_id,
        summary=getattr(state.memory, "summary", ""),
        config=CompactConfig(
            enable_context_compaction=getattr(config, "enable_context_compaction", True),
            context_keep_head_turns=getattr(config, "context_keep_head_turns", 2),
            context_keep_tail_turns=getattr(config, "context_keep_tail_turns", 6),
            tool_result_placeholder_max_chars=getattr(config, "tool_result_placeholder_max_chars", 200),
            middle_summary_max_chars=getattr(config, "middle_summary_max_chars", 1200),
            daily_memory_filename=getattr(config, "daily_memory_filename", "每日记忆.md"),
        ),
    )
    errors.extend(getattr(compact_result, "errors", []))
    return {
        "compact_context": compact_result.compact_context,
        "daily_snapshot_written": daily_snapshot_written,
        "placeholder_index": [
            record.__dict__ if hasattr(record, "__dict__") else record
            for record in compact_result.placeholder_index
        ],
        "summary_status": compact_result.summary_status,
        "fallback_used": compact_result.fallback_used,
        "errors": errors,
    }
