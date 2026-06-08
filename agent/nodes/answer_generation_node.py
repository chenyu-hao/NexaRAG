import inspect

from agent.router import get_prompt


CLARIFICATION_TEXT = "请先说明您指的是哪款产品或对象，我再帮您查询。"


class LLMAnswerGenerator:
    def __init__(self, llm, prompt_selector=get_prompt):
        self.llm = llm
        self.prompt_selector = prompt_selector

    async def generate(self, state: dict, runtime=None) -> str:
        if state.get("needs_clarification"):
            return state.get("answer", CLARIFICATION_TEXT)
        if state.get("is_chitchat"):
            response = await self.llm.ainvoke(self._build_chitchat_prompt(state))
            return response.content if hasattr(response, "content") else str(response)

        intent = state.get("intent", {}).get("intent", "product_query")
        prompt_template = self.prompt_selector(intent)
        full_input = self._build_input(state)
        prompt_text = prompt_template.format(
            context=state.get("context", ""),
            input=full_input,
        )
        response = await self.llm.ainvoke(prompt_text)
        return response.content if hasattr(response, "content") else str(response)

    async def stream(self, state: dict, runtime=None):
        if state.get("needs_clarification"):
            yield state.get("answer", CLARIFICATION_TEXT)
            return
        prompt_text = self._build_prompt_text(state)
        if hasattr(self.llm, "astream"):
            async for chunk in self.llm.astream(prompt_text):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)
                if token:
                    yield token
            return
        yield await self.generate(state, runtime)

    def _build_prompt_text(self, state: dict) -> str:
        if state.get("needs_clarification"):
            return state.get("answer", CLARIFICATION_TEXT)
        if state.get("is_chitchat"):
            return self._build_chitchat_prompt(state)

        intent = state.get("intent", {}).get("intent", "product_query")
        prompt_template = self.prompt_selector(intent)
        full_input = self._build_input(state)
        return prompt_template.format(
            context=state.get("context", ""),
            input=full_input,
        )

    @staticmethod
    def _build_input(state: dict) -> str:
        parts = []
        if state.get("memory_context"):
            parts.append(f"【长期记忆】\n{state['memory_context']}")
        if state.get("user_profile"):
            parts.append(f"【用户信息】\n{state['user_profile']}")
        if state.get("chat_history"):
            parts.append(f"【对话历史】\n{state['chat_history']}")
        if state.get("image_desc"):
            products = "、".join(state.get("detected_products", [])) or "未知"
            parts.append(
                f"【图片识别结果】\n"
                f"用户发送了图片，识别到产品: {products}\n"
                f"描述: {state['image_desc']}"
            )
        parts.append(f"【当前问题】\n{state['question']}")
        return "\n\n".join(parts)

    @classmethod
    def _build_chitchat_prompt(cls, state: dict) -> str:
        return (
            "你是友好的客服助手，简洁回复闲聊。"
            "如果用户的问题依赖前文，请参考对话历史和记忆回答。\n\n"
            f"{cls._build_input(state)}"
        )


class AnswerGenerationNode:
    def __init__(self, generator=None):
        self.generator = generator

    async def run(self, state: dict, runtime=None) -> dict:
        if state.get("needs_clarification"):
            return {"answer": state.get("answer", CLARIFICATION_TEXT)}
        if self.generator is None:
            return {"answer": state.get("answer", "")}
        answer = self.generator.generate(state, runtime)
        if inspect.isawaitable(answer):
            answer = await answer
        return {"answer": answer}

    async def stream(self, state: dict, runtime=None):
        if self.generator is None:
            answer = state.get("answer", "")
            if answer:
                yield answer
            return
        if hasattr(self.generator, "stream"):
            async for chunk in self.generator.stream(state, runtime):
                yield chunk
            return
        answer = self.generator.generate(state, runtime)
        if inspect.isawaitable(answer):
            answer = await answer
        if answer:
            yield answer
