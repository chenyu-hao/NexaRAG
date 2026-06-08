import re

from memory.query_rewriter import QueryRewriter


_AMBIGUOUS_PRONOUN_RE = re.compile(
    r"\b(it|this|that|they|them|he|she)\b|它|这个|这款|那个|该机|该产品",
    re.IGNORECASE,
)
_ENTITY_HINT_RE = re.compile(
    r"(phone|alpha|beta|gamma|pro|max|iphone|huawei|xiaomi|vivo|oppo|mate|find|小米|华为|苹果|荣耀|三星|型号)",
    re.IGNORECASE,
)


def _needs_reference_clarification(state: dict) -> bool:
    question = state.get("question", "")
    if not _AMBIGUOUS_PRONOUN_RE.search(question):
        return False
    if state.get("chat_history", "").strip():
        return False
    if state.get("image_desc") or state.get("detected_products"):
        return False
    if _ENTITY_HINT_RE.search(question):
        return False
    return True


class QueryRewriteNode:
    def __init__(self, rewriter=None, llm=None):
        self.rewriter = rewriter or QueryRewriter()
        self.llm = llm

    async def run(self, state: dict, runtime=None) -> dict:
        if state.get("is_chitchat"):
            return {"rewritten_query": state["question"]}
        if _needs_reference_clarification(state):
            return {
                "rewritten_query": state["question"],
                "needs_clarification": True,
                "answer": (
                    "Which product are you asking about? Please provide the product "
                    "name or model so I can confirm it accurately."
                ),
            }
        result = await self.rewriter.arewrite(
            state["question"],
            state.get("chat_history", ""),
            llm=self.llm,
        )
        return {"rewritten_query": result["rewritten"]}
