import json
from datetime import date, timedelta


def test_session_log_appends_jsonl_events(tmp_path):
    from memory.session_log import SessionLog

    log = SessionLog(root=tmp_path, user_id="u1", session_id="s1")

    log.append({"type": "user_message", "content": "hello"})
    log.append({"type": "assistant_message", "content": "hi"})

    path = tmp_path / "u1" / "sessions" / "s1.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()

    assert [json.loads(line)["type"] for line in lines] == [
        "user_message",
        "assistant_message",
    ]
    assert all("timestamp" in json.loads(line) for line in lines)


def test_daily_memory_appends_blocks_by_date(tmp_path):
    from memory.daily_memory import DailyMemory

    memory = DailyMemory(root=tmp_path, user_id="u1")

    memory.append("first block", day=date(2026, 6, 7))
    memory.append("second block", day=date(2026, 6, 7))

    path = tmp_path / "u1" / "daily" / "2026-06-07.md"
    text = path.read_text(encoding="utf-8")

    assert "first block" in text
    assert "second block" in text
    assert text.index("first block") < text.index("second block")


def test_daily_memory_appends_blocks_to_fixed_summary_file(tmp_path):
    from memory.daily_memory import DailyMemory

    memory = DailyMemory(root=tmp_path, user_id="u1")

    memory.append_summary("session summary")

    path = tmp_path / "u1" / "daily" / "每日记忆.md"
    assert path.exists()
    assert "session summary" in path.read_text(encoding="utf-8")


def test_stable_memory_reads_and_writes_memory_md(tmp_path):
    from memory.stable_memory import StableMemory

    memory = StableMemory(root=tmp_path, user_id="u1")

    assert memory.read() == ""

    memory.write("# Long-term Memory\n\n- likes photos")

    assert "likes photos" in memory.read()


def test_memory_context_reads_stable_today_and_yesterday(tmp_path):
    from memory.daily_memory import DailyMemory
    from memory.memory_context import MemoryContextBuilder
    from memory.stable_memory import StableMemory

    today = date(2026, 6, 7)
    yesterday = today - timedelta(days=1)

    StableMemory(root=tmp_path, user_id="u1").write("stable info")
    DailyMemory(root=tmp_path, user_id="u1").append("today info", day=today)
    DailyMemory(root=tmp_path, user_id="u1").append("yesterday info", day=yesterday)

    context = MemoryContextBuilder(root=tmp_path).build("u1", today=today)

    assert "stable info" in context
    assert "today info" in context
    assert "yesterday info" in context
    assert "【长期稳定记忆】" in context
    assert "【今日记忆】" in context
    assert "【昨日记忆】" in context
