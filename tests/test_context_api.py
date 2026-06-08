import asyncio
from types import SimpleNamespace


class FakeMemoryService:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def record_daily_snapshot(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            return SimpleNamespace(written=False, summary_written=False, errors=["daily failed"])
        return SimpleNamespace(written=True, summary_written=True, errors=[])


class FakeCompactor:
    def __init__(self):
        self.calls = []

    def compact(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            compact_context="【会话起始保留】\n用户: hi",
            placeholder_index=[],
            summary_status="none",
            fallback_used=False,
            errors=[],
        )


class FakeSessions:
    def __init__(self):
        self.state = SimpleNamespace(
            memory=SimpleNamespace(
                messages=[SimpleNamespace(role="user", content="hi", image_count=0)],
                summary="old summary",
            )
        )

    def get(self, session_id=None, user_id="default"):
        return self.state if session_id == "s1" and user_id == "u1" else None


def test_compact_context_endpoint_writes_daily_then_compacts():
    from api.context import CompactContextRequest, compact_context

    memory_service = FakeMemoryService()
    compactor = FakeCompactor()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        sessions=FakeSessions(),
        memory_service=memory_service,
        context_compactor=compactor,
    )))

    result = asyncio.run(compact_context(
        CompactContextRequest(user_id="u1", session_id="s1", write_daily_snapshot=True),
        request=request,
    ))

    assert memory_service.calls[0]["reason"] == "context_compaction"
    assert compactor.calls[0]["summary"] == "old summary"
    assert result["daily_snapshot_written"] is True
    assert result["compact_context"].startswith("【会话起始保留】")


def test_compact_context_endpoint_keeps_compacting_when_daily_fails():
    from api.context import CompactContextRequest, compact_context

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        sessions=FakeSessions(),
        memory_service=FakeMemoryService(fail=True),
        context_compactor=FakeCompactor(),
    )))

    result = asyncio.run(compact_context(
        CompactContextRequest(user_id="u1", session_id="s1", write_daily_snapshot=True),
        request=request,
    ))

    assert result["daily_snapshot_written"] is False
    assert result["compact_context"]
    assert "daily failed" in result["errors"]
