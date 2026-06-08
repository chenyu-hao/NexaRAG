import pytest


class FakeVisionAnalyzer:
    async def aanalyze(self, images, question):
        return {"description": "phone image", "detected_products": ["Mate 70 Pro"]}


class FakeIntentClassifier:
    async def aclassify(self, message, history="", llm=None, has_image=False):
        return {"intent": "product_query", "confidence": 0.9, "reason": "test"}


class FakeQueryRewriter:
    async def arewrite(self, query, chat_history="", llm=None):
        return {"rewritten": f"rewritten {query}", "needs_rewrite": True}


class FakeVerifier:
    async def averify(self, question, answer, context, llm=None):
        return {"pass": True, "score": 0.8}


class FakeToolRunner:
    async def run(self, state, runtime=None):
        return {
            "context": "retrieved context",
            "used_tools": [{"tool": "search_knowledge"}],
        }


class FakeAnswerGenerator:
    async def generate(self, state, runtime=None):
        return "final answer"

    async def stream(self, state, runtime=None):
        yield "final "
        yield "answer"


class RecordingLLM:
    def __init__(self):
        self.prompts = []

    async def ainvoke(self, prompt):
        self.prompts.append(prompt)
        return type("Response", (), {"content": "ok"})()


@pytest.mark.asyncio
async def test_vision_node_skips_empty_images_and_analyzes_images():
    from agent.nodes.vision_node import VisionNode

    node = VisionNode(analyzer=FakeVisionAnalyzer())

    assert await node.run({"images": [], "question": "q"}, None) == {
        "image_desc": "",
        "detected_products": [],
        "images": [],
    }

    result = await node.run({"images": ["img"], "question": "q"}, None)

    assert result == {
        "image_desc": "phone image",
        "detected_products": ["Mate 70 Pro"],
        "images": [],
    }


@pytest.mark.asyncio
async def test_intent_node_returns_structured_intent_and_chitchat_flag():
    from agent.nodes.intent_node import IntentNode

    node = IntentNode(classifier=FakeIntentClassifier(), llm="light")

    result = await node.run(
        {"question": "battery", "chat_history": "history", "images": ["img"]},
        None,
    )

    assert result == {
        "intent": {"intent": "product_query", "confidence": 0.9},
        "intent_confidence": 0.9,
        "is_chitchat": False,
    }


@pytest.mark.asyncio
async def test_query_rewrite_node_skips_chitchat_and_rewrites_business_query():
    from agent.nodes.query_rewrite_node import QueryRewriteNode

    node = QueryRewriteNode(rewriter=FakeQueryRewriter(), llm="chat")

    assert await node.run({"question": "hi", "is_chitchat": True}, None) == {
        "rewritten_query": "hi"
    }

    ambiguous = await node.run(
        {
            "question": "Does it support wireless charging?",
            "chat_history": "",
            "is_chitchat": False,
        },
        None,
    )

    assert ambiguous["needs_clarification"] is True
    assert "which product" in ambiguous["answer"].lower()

    result = await node.run(
        {"question": "battery", "chat_history": "history", "is_chitchat": False},
        None,
    )

    assert result == {"rewritten_query": "rewritten battery"}


@pytest.mark.asyncio
async def test_verification_node_skips_chitchat_and_verifies_business_answer():
    from agent.nodes.verification_node import VerificationNode

    node = VerificationNode(verifier=FakeVerifier(), llm="light")

    assert await node.run({"is_chitchat": True}, None) == {"verification": {}}

    result = await node.run(
        {
            "question": "battery",
            "answer": "5000mAh",
            "context": "battery 5000mAh",
            "is_chitchat": False,
        },
        None,
    )

    assert result == {"verification": {"pass": True, "score": 0.8}}

    assert await node.run(
        {"needs_clarification": True, "answer": "Which product?", "is_chitchat": False},
        None,
    ) == {"verification": {}}


@pytest.mark.asyncio
async def test_tool_reasoning_node_skips_chitchat_and_runs_tool_runner():
    from agent.nodes.tool_reasoning_node import ToolReasoningNode

    node = ToolReasoningNode(runner=FakeToolRunner())

    assert await node.run({"is_chitchat": True}, None) == {
        "context": "闲聊",
        "used_tools": [],
    }
    assert await node.run({"needs_clarification": True}, None) == {
        "context": "",
        "used_tools": [],
    }

    result = await node.run({"is_chitchat": False, "question": "battery"}, None)

    assert result == {
        "context": "retrieved context",
        "used_tools": [{"tool": "search_knowledge"}],
    }


@pytest.mark.asyncio
async def test_answer_generation_node_uses_generator():
    from agent.nodes.answer_generation_node import AnswerGenerationNode

    node = AnswerGenerationNode(generator=FakeAnswerGenerator())

    result = await node.run({"question": "battery", "context": "ctx"}, None)

    assert result == {"answer": "final answer"}

    clarification = await node.run(
        {"needs_clarification": True, "answer": "Which product?"},
        None,
    )

    assert clarification == {"answer": "Which product?"}


@pytest.mark.asyncio
async def test_answer_generation_node_streams_when_generator_supports_stream():
    from agent.nodes.answer_generation_node import AnswerGenerationNode

    node = AnswerGenerationNode(generator=FakeAnswerGenerator())

    chunks = []
    async for chunk in node.stream({"question": "battery", "context": "ctx"}, None):
        chunks.append(chunk)

    assert chunks == ["final ", "answer"]


@pytest.mark.asyncio
async def test_chitchat_answer_generation_includes_chat_history():
    from agent.nodes.answer_generation_node import LLMAnswerGenerator

    llm = RecordingLLM()
    generator = LLMAnswerGenerator(llm=llm)

    answer = await generator.generate({
        "question": "What is my name?",
        "is_chitchat": True,
        "chat_history": "User: My name is Alice\nAssistant: Nice to meet you",
    })

    assert answer == "ok"
    assert "My name is Alice" in llm.prompts[0]
    assert "What is my name?" in llm.prompts[0]
