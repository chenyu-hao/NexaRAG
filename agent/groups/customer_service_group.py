from __future__ import annotations

import inspect

from agent.runtime import AgentRuntime
from agent.schemas import AgentInput, AgentOutput
from agent.nodes.answer_generation_node import AnswerGenerationNode, LLMAnswerGenerator
from agent.nodes.intent_node import IntentNode
from agent.nodes.query_rewrite_node import QueryRewriteNode
from agent.nodes.tool_reasoning_node import LLMToolReasoningRunner, ToolReasoningNode
from agent.nodes.verification_node import VerificationNode
from agent.nodes.vision_node import VisionNode
from tools.toolsets import build_customer_service_toolset


class CustomerServiceAgentGroup:
    """Coordinates agent nodes and returns an AgentOutput."""

    def __init__(self, nodes: list | None = None):
        self.nodes = list(nodes or [])
        self.last_output: AgentOutput | None = None

    async def run(self, agent_input: AgentInput, runtime: AgentRuntime | None = None) -> AgentOutput:
        runtime = runtime or AgentRuntime()
        state = agent_input.to_state()
        for node in self.nodes:
            self._record(runtime, {"type": "node_started", "node": node.__class__.__name__})
            update = node.run(state, runtime)
            if inspect.isawaitable(update):
                update = await update
            if update:
                state.update(update)
            self._record(runtime, {"type": "node_finished", "node": node.__class__.__name__})
        self.last_output = AgentOutput.from_state(state)
        return self.last_output

    async def stream(self, agent_input: AgentInput, runtime: AgentRuntime | None = None):
        runtime = runtime or AgentRuntime()
        state = agent_input.to_state()
        for node in self.nodes:
            self._record(runtime, {"type": "node_started", "node": node.__class__.__name__})
            if hasattr(node, "stream"):
                chunks = []
                async for chunk in node.stream(state, runtime):
                    chunks.append(chunk)
                    yield chunk
                if chunks:
                    state["answer"] = "".join(chunks)
                self._record(runtime, {"type": "node_finished", "node": node.__class__.__name__})
                continue
            update = node.run(state, runtime)
            if inspect.isawaitable(update):
                update = await update
            if update:
                state.update(update)
            self._record(runtime, {"type": "node_finished", "node": node.__class__.__name__})
        self.last_output = AgentOutput.from_state(state)

    @staticmethod
    def _record(runtime: AgentRuntime, event: dict):
        if runtime.recorder is not None:
            runtime.recorder.record(event)


def build_customer_service_group(
    vision_analyzer,
    intent_classifier,
    chat_llm,
    light_llm,
    react_llm,
    knowledge_base,
):
    tools = build_customer_service_toolset(knowledge_base)
    return CustomerServiceAgentGroup(nodes=[
        VisionNode(analyzer=vision_analyzer),
        IntentNode(classifier=intent_classifier, llm=light_llm),
        QueryRewriteNode(llm=chat_llm),
        ToolReasoningNode(runner=LLMToolReasoningRunner(
            llm=react_llm,
            tools=tools,
        )),
        AnswerGenerationNode(generator=LLMAnswerGenerator(llm=chat_llm)),
        VerificationNode(llm=light_llm),
    ])
