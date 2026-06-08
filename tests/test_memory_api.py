from datetime import date
import asyncio
from types import SimpleNamespace


class FakeMemoryService:
    def __init__(self):
        self.calls = []

    def promote_daily_to_stable(self, user_id, day=None, dry_run=False):
        self.calls.append((user_id, day, dry_run))
        return SimpleNamespace(
            promoted=["我喜欢简洁答案"],
            skipped=[],
            memory_path="data/memory/u1/memory.md",
            errors=[],
        )


def test_promote_daily_endpoint_uses_memory_service():
    from api.memory import PromoteDailyRequest, promote_daily

    service = FakeMemoryService()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(memory_service=service)))

    result = asyncio.run(
        promote_daily(
            PromoteDailyRequest(user_id="u1", date="2026-06-08", dry_run=True),
            request=request,
        )
    )

    assert service.calls == [("u1", date(2026, 6, 8), True)]
    assert result["promoted"] == ["我喜欢简洁答案"]
    assert result["skipped"] == []
    assert result["memory_path"] == "data/memory/u1/memory.md"
