from __future__ import annotations


class LLMToolRunner:
    """Runs an LLM with a supplied toolset."""

    def __init__(self, llm, tools: list):
        self.llm = llm
        self.tools = list(tools)

    def bind(self):
        return self.llm.bind_tools(self.tools)
