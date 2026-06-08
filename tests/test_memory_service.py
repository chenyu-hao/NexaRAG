from datetime import date


def test_record_daily_snapshot_writes_actions_and_candidates(tmp_path):
    from memory.memory_service import MemoryService

    service = MemoryService(root=tmp_path)

    result = service.record_daily_snapshot(
        user_id="u1",
        session_id="s1",
        messages=[{"role": "user", "content": "以后记住我喜欢简洁答案"}],
        events=[{"type": "tool_finished", "summary": "searched knowledge base"}],
        reason="manual_test",
        day=date(2026, 6, 8),
    )

    daily_path = tmp_path / "u1" / "daily" / result.date_filename
    text = daily_path.read_text(encoding="utf-8")
    summary_text = (tmp_path / "u1" / "daily" / "每日记忆.md").read_text(encoding="utf-8")

    assert result.written is True
    assert result.errors == []
    assert "manual_test" in text
    assert "searched knowledge base" in text
    assert "以后记住我喜欢简洁答案" in text
    assert "长期记忆候选" in text
    assert "manual_test" in summary_text


def test_record_daily_snapshot_write_failure_returns_error(tmp_path):
    from memory.memory_service import MemoryService

    service = MemoryService(root=tmp_path)
    service.daily_memory_cls = BrokenDailyMemory

    result = service.record_daily_snapshot(
        user_id="u1",
        session_id="s1",
        messages=[{"role": "user", "content": "hello"}],
        events=[],
        reason="manual_test",
    )

    assert result.written is False
    assert result.errors


def test_promote_daily_memory_writes_stable_memory(tmp_path):
    from memory.daily_memory import DailyMemory
    from memory.memory_service import MemoryService

    DailyMemory(tmp_path, "u1").append(
        "### 长期记忆候选\n- 以后记住我喜欢简洁答案",
        day=date(2026, 6, 8),
    )

    result = MemoryService(tmp_path).promote_daily_to_stable(
        user_id="u1",
        day=date(2026, 6, 8),
    )

    stable = (tmp_path / "u1" / "memory.md").read_text(encoding="utf-8")
    assert result.promoted_count == 1
    assert "我喜欢简洁答案" in stable
    assert result.skipped == []


def test_promote_daily_memory_deduplicates_existing_stable_memory(tmp_path):
    from memory.daily_memory import DailyMemory
    from memory.memory_service import MemoryService
    from memory.stable_memory import StableMemory

    DailyMemory(tmp_path, "u1").append(
        "### 长期记忆候选\n- 以后记住我喜欢简洁答案",
        day=date(2026, 6, 8),
    )
    StableMemory(tmp_path, "u1").write("# Long-term Memory\n\n- 我喜欢简洁答案\n")

    result = MemoryService(tmp_path).promote_daily_to_stable(
        user_id="u1",
        day=date(2026, 6, 8),
    )

    stable = (tmp_path / "u1" / "memory.md").read_text(encoding="utf-8")
    assert result.promoted_count == 0
    assert stable.count("我喜欢简洁答案") == 1
    assert "我喜欢简洁答案" in result.skipped[0]


class BrokenDailyMemory:
    def __init__(self, *args, **kwargs):
        pass

    def append(self, *args, **kwargs):
        raise OSError("cannot write daily memory")
