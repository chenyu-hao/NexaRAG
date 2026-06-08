from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeContext:
    user_id: str
    session_id: str | None = None
    request_id: str | None = None
    recorder: object | None = None
    memory_context: str = ""
