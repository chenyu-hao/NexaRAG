from datetime import date


def test_file_memory_reader_tools_read_three_layer_memory(tmp_path):
    from memory.daily_memory import DailyMemory
    from memory.session_log import SessionLog
    from memory.stable_memory import StableMemory
    from tools.memory_tools import FileMemoryReader, build_memory_tools

    StableMemory(root=tmp_path, user_id="u1").write("stable info")
    DailyMemory(root=tmp_path, user_id="u1").append("today info", day=date(2026, 6, 7))
    SessionLog(root=tmp_path, user_id="u1", session_id="s1").append({
        "type": "user_message",
        "content": "battery question",
    })

    reader = FileMemoryReader(root=tmp_path, today=date(2026, 6, 7))
    tool_map = {tool.name: tool for tool in build_memory_tools(reader)}

    assert "stable info" in tool_map["read_stable_memory"].invoke({"user_id": "u1"})
    assert "today info" in tool_map["read_daily_memory"].invoke({
        "user_id": "u1",
        "date": "2026-06-07",
    })
    assert "battery question" in tool_map["search_session_log"].invoke({
        "user_id": "u1",
        "query": "battery",
    })
    assert "stable info" in tool_map["get_memory_context"].invoke({"user_id": "u1"})
