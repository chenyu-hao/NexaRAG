from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolTrace:
    tool_name: str
    args: dict = field(default_factory=dict)
    result: str = ""
