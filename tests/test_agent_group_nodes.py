import pytest


class RecordingNode:
    def __init__(self, name, update):
        self.name = name
        self.update = update
        self.calls = []

    async def run(self, state, runtime):
        self.calls.append((dict(state), runtime))
        return dict(self.update)


class StreamingNode:
    async def stream(self, state, runtime):
        yield "hello "
        yield "stream"


class VerifyAfterStreamNode:
    def __init__(self):
        self.answer_seen = ""

    async def run(self, state, runtime):
        self.answer_seen = state.get("answer", "")
        return {"verification": {"pass": True}}


class FakeRecorder:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)


@pytest.mark.asyncio
async def test_customer_service_group_runs_nodes_in_order_and_returns_output():
    from agent.groups.customer_service_group import CustomerServiceAgentGroup
    from agent.schemas import AgentInput

    nodes = [
        RecordingNode("intent", {"intent": {"intent": "product_query"}}),
        RecordingNode("answer", {"answer": "hello"}),
        RecordingNode("verify", {"verification": {"pass": True}}),
    ]
    group = CustomerServiceAgentGroup(nodes=nodes)

    output = await group.run(AgentInput(question="hi", user_id="u1"))

    assert output.answer == "hello"
    assert output.intent == {"intent": "product_query"}
    assert output.verification == {"pass": True}
    assert [node.name for node in nodes] == ["intent", "answer", "verify"]
    assert nodes[1].calls[0][0]["intent"] == {"intent": "product_query"}


@pytest.mark.asyncio
async def test_customer_service_group_does_not_persist_memory():
    from agent.groups.customer_service_group import CustomerServiceAgentGroup
    from agent.schemas import AgentInput

    group = CustomerServiceAgentGroup(nodes=[
        RecordingNode("answer", {"answer": "no writes"}),
    ])

    output = await group.run(AgentInput(question="hi", user_id="u1"))

    assert output.answer == "no writes"
    assert not hasattr(group, "memory")
    assert not hasattr(group, "sessions")


def test_build_customer_service_group_wires_default_node_order():
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
async def test_customer_service_group_streams_answer_and_continues_nodes():
    from agent.groups.customer_service_group import CustomerServiceAgentGroup
    from agent.schemas import AgentInput

    verifier = VerifyAfterStreamNode()
    group = CustomerServiceAgentGroup(nodes=[
        RecordingNode("intent", {"intent": {"intent": "product_query"}}),
        StreamingNode(),
        verifier,
    ])

    chunks = []
    async for chunk in group.stream(AgentInput(question="hi", user_id="u1")):
        chunks.append(chunk)

    assert chunks == ["hello ", "stream"]
    assert verifier.answer_seen == "hello stream"
    assert group.last_output.answer == "hello stream"
    assert group.last_output.verification == {"pass": True}


@pytest.mark.asyncio
async def test_customer_service_group_records_node_events():
    from agent.groups.customer_service_group import CustomerServiceAgentGroup
    from agent.runtime import AgentRuntime
    from agent.schemas import AgentInput

    recorder = FakeRecorder()
    group = CustomerServiceAgentGroup(nodes=[
        RecordingNode("intent", {"intent": {"intent": "product_query"}}),
    ])

    await group.run(AgentInput(question="hi"), runtime=AgentRuntime(recorder=recorder))

    assert [event["type"] for event in recorder.events] == [
        "node_started",
        "node_finished",
    ]
    assert recorder.events[0]["node"] == "RecordingNode"
