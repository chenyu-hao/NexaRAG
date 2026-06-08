from agent.verifier import AnswerVerifier


class VerificationNode:
    def __init__(self, verifier=None, llm=None):
        self.verifier = verifier or AnswerVerifier()
        self.llm = llm

    async def run(self, state: dict, runtime=None) -> dict:
        if state.get("is_chitchat"):
            return {"verification": {}}
        if state.get("needs_clarification"):
            return {"verification": {}}
        if not state.get("answer", "").strip():
            return {"verification": {}}
        result = await self.verifier.averify(
            state["question"],
            state["answer"],
            state.get("context", ""),
            llm=self.llm,
        )
        return {"verification": result}
