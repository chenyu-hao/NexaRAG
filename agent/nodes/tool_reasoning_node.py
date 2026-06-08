import inspect

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from agent.router import get_prompt


def _build_tool_input(state: dict) -> str:
    parts = []
    if state.get("memory_context"):
        parts.append(f"【长期记忆】\n{state['memory_context']}")
    if state.get("user_profile"):
        parts.append(f"【用户画像】\n{state['user_profile']}")
    if state.get("chat_history"):
        parts.append(f"【对话历史】\n{state['chat_history']}")
    if state.get("image_desc"):
        products = "、".join(state.get("detected_products", [])) or "未知"
        parts.append(
            f"【图片识别】用户发送了图片，识别到产品: {products}\n"
            f"描述: {state['image_desc']}"
        )
    parts.append(f"【用户问题】\n{state['question']}")
    return "\n\n".join(parts)


class LLMToolReasoningRunner:
    def __init__(self, llm, tools: list, max_iterations: int = 5):
        self.llm = llm
        self.tools = list(tools)
        self.max_iterations = max_iterations

    async def run(self, state: dict, runtime=None) -> dict:
        tool_map = {tool.name: tool for tool in self.tools}
        llm_with_tools = self.llm.bind_tools(self.tools)
        intent = state.get("intent", {}).get("intent", "product_query")
        prompt_template = get_prompt(intent)
        system_text = prompt_template.messages[0].prompt.template
        messages = [
            SystemMessage(content=(
                f"{system_text}\n\n"
                "你可以使用工具搜索知识库来获得准确信息。"
                "信息充分后，不要继续调用工具。"
            )),
            HumanMessage(content=_build_tool_input(state)),
        ]
        context_chunks = []
        used_tools = []

        for _ in range(self.max_iterations):
            response = await llm_with_tools.ainvoke(messages)
            tool_calls = getattr(response, "tool_calls", []) or []
            if not tool_calls:
                break
            messages.append(response)
            for tool_call in tool_calls:
                name = tool_call["name"]
                args = tool_call.get("args", {})
                tool = tool_map.get(name)
                if tool is None:
                    result = f"[错误] 未知工具: {name}"
                else:
                    result = str(tool.invoke(args))
                context_chunks.append(result)
                used_tools.append({"name": name, "args": args})
                messages.append(ToolMessage(
                    content=result,
                    tool_call_id=tool_call.get("id", name),
                ))

        return {
            "context": "\n\n".join(context_chunks),
            "used_tools": used_tools,
        }


class ToolReasoningNode:
    def __init__(self, runner=None):
        self.runner = runner

    async def run(self, state: dict, runtime=None) -> dict:
        if state.get("is_chitchat"):
            return {"context": "闲聊", "used_tools": []}
        if state.get("needs_clarification"):
            return {"context": "", "used_tools": []}
        if self.runner is None:
            return {"context": "", "used_tools": []}
        result = self.runner.run(state, runtime)
        if inspect.isawaitable(result):
            result = await result
        return {
            "context": result.get("context", ""),
            "used_tools": result.get("used_tools", []),
        }
