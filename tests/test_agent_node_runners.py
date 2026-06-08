class FakeTool:
    name = "search_knowledge"

    def __init__(self):
        self.calls = []

    def invoke(self, args):
        self.calls.append(args)
        return "tool context"


class FakeToolCallResponse:
    content = ""

    def __init__(self, tool_calls):
        self.tool_calls = tool_calls


class FakeToolCallingLLM:
    def __init__(self):
        self.bound_tools = []
        self.messages = []
        self.calls = 0

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    async def ainvoke(self, messages):
        self.messages.append(messages)
        self.calls += 1
        if self.calls == 1:
            return FakeToolCallResponse([
                {
                    "name": "search_knowledge",
                    "args": {"query": "battery", "top_k": 1},
                    "id": "call-1",
                }
            ])
        return FakeToolCallResponse([])


class FakeTextResponse:
    def __init__(self, content):
        self.content = content


class FakeAnswerLLM:
    def __init__(self):
        self.prompts = []

    async def ainvoke(self, prompt):
        self.prompts.append(prompt)
        return FakeTextResponse("generated answer")


def fake_prompt_selector(intent):
    class Prompt:
        def format(self, context, input):
            return f"intent={intent}\ncontext={context}\ninput={input}"

    return Prompt()


async def test_llm_tool_reasoning_runner_executes_tool_calls():
    from agent.nodes.tool_reasoning_node import LLMToolReasoningRunner

    tool = FakeTool()
    llm = FakeToolCallingLLM()
    runner = LLMToolReasoningRunner(llm=llm, tools=[tool])

    result = await runner.run(
        {
            "question": "battery",
            "intent": {"intent": "product_query"},
            "user_profile": "",
            "chat_history": "",
            "image_desc": "",
            "detected_products": [],
        },
        None,
    )

    assert result["context"] == "tool context"
    assert result["used_tools"] == [
        {"name": "search_knowledge", "args": {"query": "battery", "top_k": 1}}
    ]
    assert tool.calls == [{"query": "battery", "top_k": 1}]
    assert llm.bound_tools == [tool]
    human_message = llm.messages[0][1]
    assert "【长期记忆】" not in human_message.content


async def test_llm_tool_reasoning_runner_includes_memory_context():
    from agent.nodes.tool_reasoning_node import LLMToolReasoningRunner

    tool = FakeTool()
    llm = FakeToolCallingLLM()
    runner = LLMToolReasoningRunner(llm=llm, tools=[tool])

    await runner.run(
        {
            "question": "private code?",
            "intent": {"intent": "product_query"},
            "user_profile": "",
            "chat_history": "",
            "memory_context": "private code ABC-123",
            "image_desc": "",
            "detected_products": [],
        },
        None,
    )

    human_message = llm.messages[0][1]
    assert "【长期记忆】" in human_message.content
    assert "private code ABC-123" in human_message.content


async def test_llm_answer_generator_uses_prompt_selector():
    from agent.nodes.answer_generation_node import LLMAnswerGenerator

    llm = FakeAnswerLLM()
    generator = LLMAnswerGenerator(llm=llm, prompt_selector=fake_prompt_selector)

    answer = await generator.generate(
        {
            "question": "battery?",
            "intent": {"intent": "product_query"},
            "context": "tool context",
            "chat_history": "old chat",
            "user_profile": "likes photos",
            "memory_context": "private code ABC-123",
            "image_desc": "",
            "detected_products": [],
            "is_chitchat": False,
        },
        None,
    )

    assert answer == "generated answer"
    assert "intent=product_query" in llm.prompts[0]
    assert "context=tool context" in llm.prompts[0]
    assert "battery?" in llm.prompts[0]
    assert "private code ABC-123" in llm.prompts[0]
