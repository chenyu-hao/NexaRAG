from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentRuntime:
    recorder: object | None = None
    stream_writer: object | None = None
