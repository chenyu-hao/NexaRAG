import pytest


class FakeProfileExtractor:
    async def aextract(self, context, llm=None):
        return {
            "profile": {"budget": "5000"},
            "preferences": ["拍照"],
            "mentioned_products": ["Mate 70 Pro"],
            "summary": "用户关注拍照手机",
        }


class FakeLongTermMemory:
    def __init__(self):
        self.profile = None
        self.preferences = []
        self.products = []
        self.summaries = []

    def update_profile(self, profile):
        self.profile = profile

    def add_preference(self, preference):
        self.preferences.append(preference)

    def add_mentioned_product(self, product):
        self.products.append(product)

    def add_session_summary(self, summary):
        self.summaries.append(summary)


class FakeConversationMemory:
    is_empty = False

    def get_context_string(self):
        return "用户: 我预算5000，关注拍照"


@pytest.mark.asyncio
async def test_agent_dependencies_extracts_long_term_memory_on_session_end():
    from agent.dependencies import AgentDependencies

    long_memory = FakeLongTermMemory()
    deps = AgentDependencies(
        llm="chat",
        light_llm="light",
        react_llm="react",
        vision_analyzer="vision",
        intent_classifier="intent",
        profile_extractor=FakeProfileExtractor(),
        long_term_factory=lambda user_id: long_memory,
    )

    await deps.end_session("u1", FakeConversationMemory())

    assert long_memory.profile == {"budget": "5000"}
    assert long_memory.preferences == ["拍照"]
    assert long_memory.products == ["Mate 70 Pro"]
    assert long_memory.summaries == ["用户关注拍照手机"]
