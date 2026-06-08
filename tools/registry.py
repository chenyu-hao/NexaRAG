from __future__ import annotations


class ToolRegistry:
    """Stores named groups of LLM-callable tools."""

    def __init__(self):
        self._toolsets: dict[str, list] = {}

    def register_many(self, name: str, tools: list):
        self._toolsets[name] = list(tools)

    def get_toolset(self, name: str) -> list:
        return list(self._toolsets.get(name, []))

    def all_tools(self) -> list:
        result = []
        for tools in self._toolsets.values():
            result.extend(tools)
        return result
