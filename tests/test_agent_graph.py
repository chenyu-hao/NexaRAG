import pytest


class DummyNode:
    async def run(self, state, runtime):
        return {}


class AnswerNode:
    async def run(self, state, runtime):
        return {"answer": "ok"}


class VerificationNode:
    async def run(self, state, runtime):
        return {"verification": {"pass": True}}


@pytest.mark.asyncio
async def test_agent_group_built():
    from agent.groups.customer_service_group import CustomerServiceAgentGroup
    from agent.schemas import AgentInput

    group = CustomerServiceAgentGroup(nodes=[AnswerNode()])

    output = await group.run(AgentInput(question="hello"))

    assert output.answer == "ok"


def test_customer_service_group_uses_node_order():
    from agent.groups.customer_service_group import build_customer_service_group

    group = build_customer_service_group(
        vision_analyzer="vision",
        intent_classifier="intent",
        chat_llm="chat",
        light_llm="light",
        react_llm="react",
        knowledge_base="knowledge",
    )

    assert [node.__class__.__name__ for node in group.nodes] == [
        "VisionNode",
        "IntentNode",
        "QueryRewriteNode",
        "ToolReasoningNode",
        "AnswerGenerationNode",
        "VerificationNode",
    ]


@pytest.mark.asyncio
async def test_agent_group_has_edges_by_sequential_node_execution():
    from agent.groups.customer_service_group import CustomerServiceAgentGroup
    from agent.schemas import AgentInput

    calls = []

    class RecordingNode:
        def __init__(self, name):
            self.name = name

        async def run(self, state, runtime):
            calls.append(self.name)
            return {"answer": self.name}

    group = CustomerServiceAgentGroup(nodes=[
        RecordingNode("vision"),
        RecordingNode("intent"),
        RecordingNode("answer"),
    ])

    output = await group.run(AgentInput(question="hello"))

    assert calls == ["vision", "intent", "answer"]
    assert output.answer == "answer"
