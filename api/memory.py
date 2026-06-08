from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api/memory", tags=["记忆"])


class PromoteDailyRequest(BaseModel):
    user_id: str = "default"
    date: str | None = None
    dry_run: bool = False


def _get_memory_service(request: Request):
    return request.app.state.memory_service


@router.post("/promote-daily")
async def promote_daily(req: PromoteDailyRequest, request: Request):
    day = date.fromisoformat(req.date) if req.date else None
    result = _get_memory_service(request).promote_daily_to_stable(
        user_id=req.user_id,
        day=day,
        dry_run=req.dry_run,
    )
    return {
        "promoted": result.promoted,
        "skipped": result.skipped,
        "memory_path": result.memory_path,
        "errors": result.errors,
    }
