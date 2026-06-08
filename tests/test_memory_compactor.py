from memory.memory_compactor import CompactConfig, MemoryCompactor


def test_compactor_empty_messages_returns_empty_context():
    compactor = MemoryCompactor()

    result = compactor.compact(
        messages=[],
        session_id="s1",
        user_id="u1",
        summary="",
        config=CompactConfig(),
    )

    assert result.compact_context == ""
    assert result.placeholder_index == []
    assert result.summary_status == "none"
    assert result.daily_memory_written is False
    assert result.fallback_used is False
    assert result.errors == []


def test_compactor_short_conversation_does_not_create_middle_summary():
    compactor = MemoryCompactor()
    messages = [
        {"role": "user", "content": "请记住我的目标是修复检索。"},
        {"role": "assistant", "content": "好的，我会保留这个目标。"},
    ]

    result = compactor.compact(
        messages=messages,
        session_id="s1",
        user_id="u1",
        summary="",
        config=CompactConfig(context_keep_head_turns=2, context_keep_tail_turns=6),
    )

    assert "【会话起始保留】" in result.compact_context
    assert "用户: 请记住我的目标是修复检索。" in result.compact_context
    assert "助手: 好的，我会保留这个目标。" in result.compact_context
    assert "【中间任务摘要】" not in result.compact_context
    assert result.summary_status == "none"


def test_compactor_replaces_large_tool_result_with_placeholder():
    compactor = MemoryCompactor()
    raw_tool_result = "RAW_TOOL_RESULT_" * 20

    result = compactor.compact(
        messages=[
            {"role": "user", "content": "查一下资料"},
            {"role": "tool", "name": "search", "content": raw_tool_result, "args": {"q": "资料"}},
            {"role": "assistant", "content": "已查到资料。"},
        ],
        session_id="s1",
        user_id="u1",
        config=CompactConfig(tool_result_placeholder_max_chars=30),
    )

    assert raw_tool_result not in result.compact_context
    assert "[TOOL_RESULT_PLACEHOLDER: tool=search, index=1" in result.compact_context
    assert result.placeholder_index[0].tool == "search"
    assert result.placeholder_index[0].chars == len(raw_tool_result)


def test_compactor_keeps_head_and_tail_turns_and_summarizes_middle():
    compactor = MemoryCompactor()
    messages = []
    for index in range(5):
        messages.append({"role": "user", "content": f"任务 {index}"})
        messages.append({"role": "assistant", "content": f"回复 {index}"})

    result = compactor.compact(
        messages=messages,
        session_id="s1",
        user_id="u1",
        config=CompactConfig(context_keep_head_turns=1, context_keep_tail_turns=1),
        llm=FakeLLM("【中间任务摘要】\n已完成：\n- 中间任务已处理"),
    )

    assert "用户: 任务 0" in result.compact_context
    assert "助手: 回复 0" in result.compact_context
    assert "用户: 任务 4" in result.compact_context
    assert "助手: 回复 4" in result.compact_context
    assert "用户: 任务 2" not in result.compact_context
    assert "中间任务已处理" in result.compact_context
    assert result.summary_status == "llm"


def test_compactor_deduplicates_overlapped_head_and_tail_turns():
    compactor = MemoryCompactor()
    messages = [
        {"role": "user", "content": "任务 0"},
        {"role": "assistant", "content": "回复 0"},
        {"role": "user", "content": "任务 1"},
        {"role": "assistant", "content": "回复 1"},
    ]

    result = compactor.compact(
        messages=messages,
        session_id="s1",
        user_id="u1",
        config=CompactConfig(context_keep_head_turns=2, context_keep_tail_turns=2),
    )

    assert result.compact_context.count("用户: 任务 0") == 1
    assert result.compact_context.count("用户: 任务 1") == 1
    assert "【中间任务摘要】" not in result.compact_context


def test_compactor_uses_rule_summary_when_llm_fails():
    compactor = MemoryCompactor()
    messages = []
    for index in range(4):
        messages.append({"role": "user", "content": f"请处理第 {index} 件事"})
        messages.append({"role": "assistant", "content": f"处理第 {index} 件事"})

    result = compactor.compact(
        messages=messages,
        session_id="s1",
        user_id="u1",
        config=CompactConfig(context_keep_head_turns=1, context_keep_tail_turns=1),
        llm=FailingLLM(),
    )

    assert result.summary_status == "fallback"
    assert result.fallback_used is True
    assert "LLM 摘要不可用，使用规则摘要" in result.compact_context
    assert "请处理第 1 件事" in result.compact_context


class FakeLLM:
    def __init__(self, content):
        self.content = content

    def invoke(self, prompt):
        self.prompt = prompt
        return type("LLMResult", (), {"content": self.content})()


class FailingLLM:
    def invoke(self, prompt):
        raise RuntimeError("llm unavailable")
