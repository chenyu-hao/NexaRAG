from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentInput:
    question: str
    user_id: str = "default"
    session_id: str | None = None
    chat_history: str = ""
    user_profile: str = ""
    images: list[str] = field(default_factory=list)
    memory_context: str = ""

    def to_state(self) -> dict:
        return {
            "question": self.question,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "chat_history": self.chat_history,
            "user_profile": self.user_profile,
            "images": list(self.images),
            "memory_context": self.memory_context,
            "intent": {},
            "rewritten_query": "",
            "context": "",
            "answer": "",
            "verification": {},
            "image_desc": "",
            "detected_products": [],
            "used_tools": [],
        }


@dataclass
class AgentOutput:
    answer: str
    intent: dict = field(default_factory=dict)
    verification: dict = field(default_factory=dict)
    context: str = ""
    rewritten_query: str = ""
    image_desc: str = ""
    detected_products: list[str] = field(default_factory=list)
    used_tools: list[dict] = field(default_factory=list)

    @classmethod
    def from_state(cls, state: dict) -> "AgentOutput":
        return cls(
            answer=state.get("answer", ""),
            intent=state.get("intent", {}),
            verification=state.get("verification", {}),
            context=state.get("context", ""),
            rewritten_query=state.get("rewritten_query", ""),
            image_desc=state.get("image_desc", ""),
            detected_products=state.get("detected_products", []),
            used_tools=state.get("used_tools", []),
        )
