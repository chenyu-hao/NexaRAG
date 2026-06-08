from agent.intent import IntentClassifier


class IntentNode:
    def __init__(self, classifier=None, llm=None):
        self.classifier = classifier or IntentClassifier()
        self.llm = llm

    async def run(self, state: dict, runtime=None) -> dict:
        result = await self.classifier.aclassify(
            state["question"],
            state.get("chat_history", ""),
            llm=self.llm,
            has_image=bool(state.get("images", [])),
        )
        intent = result["intent"]
        confidence = result.get("confidence", 0)
        return {
            "intent": {"intent": intent, "confidence": confidence},
            "intent_confidence": confidence,
            "is_chitchat": intent == "chitchat",
        }
