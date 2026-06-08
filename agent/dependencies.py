from __future__ import annotations

from langchain_community.chat_models import ChatTongyi

from agent.intent import IntentClassifier
from agent.vision import VisionAnalyzer
from config import settings as config
from memory.long_term import LongTermMemory
from memory.user_profile import UserProfileExtractor


class AgentDependencies:
    """Holds model and agent-side dependencies outside core."""

    def __init__(
        self,
        llm,
        light_llm,
        react_llm,
        vision_analyzer,
        intent_classifier,
        profile_extractor=None,
        long_term_factory=None,
    ):
        self.llm = llm
        self.light_llm = light_llm
        self.react_llm = react_llm
        self.vision_analyzer = vision_analyzer
        self.intent_classifier = intent_classifier
        self.profile_extractor = profile_extractor or UserProfileExtractor()
        self.long_term_factory = long_term_factory or LongTermMemory
        self._long_term_cache = {}

    @classmethod
    def from_config(cls) -> "AgentDependencies":
        return cls(
            llm=ChatTongyi(
                model=config.chat_model,
                dashscope_api_key=config.dashscope_api_key,
                streaming=True,
            ),
            light_llm=ChatTongyi(
                model=config.classifier_model,
                dashscope_api_key=config.dashscope_api_key,
                temperature=0,
            ),
            react_llm=ChatTongyi(
                model=config.chat_model,
                dashscope_api_key=config.dashscope_api_key,
                streaming=False,
            ),
            vision_analyzer=VisionAnalyzer(),
            intent_classifier=IntentClassifier(),
        )

    def get_long_term(self, user_id: str):
        if user_id not in self._long_term_cache:
            self._long_term_cache[user_id] = self.long_term_factory(user_id)
        return self._long_term_cache[user_id]

    async def end_session(self, user_id: str, memory):
        if memory.is_empty:
            return
        long_mem = self.get_long_term(user_id)
        extracted = await self.profile_extractor.aextract(
            memory.get_context_string(),
            llm=self.light_llm,
        )
        if extracted.get("profile"):
            long_mem.update_profile(extracted["profile"])
        for preference in extracted.get("preferences", []):
            long_mem.add_preference(preference)
        for product in extracted.get("mentioned_products", []):
            long_mem.add_mentioned_product(product)
        if extracted.get("summary"):
            long_mem.add_session_summary(extracted["summary"])
