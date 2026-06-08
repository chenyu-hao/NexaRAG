from types import SimpleNamespace

import pytest
from fastapi import HTTPException


class FakeChatService:
    def __init__(self):
        self.calls = []

    async def chat(self, question, session_id=None, user_id="default", images=None):
        self.calls.append((question, session_id, user_id, images))
        return {
            "answer": "ok",
            "session_id": session_id or "new12345",
            "turn_count": 1,
            "intent": {"intent": "product_query"},
            "verification": {},
        }


@pytest.mark.asyncio
async def test_chat_api_uses_chat_service_without_rag_or_sessions_state():
    from api.chat import ChatRequest, chat

    service = FakeChatService()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(chat=service)))

    result = await chat(
        ChatRequest(question="hello", session_id=None, user_id="u1"),
        request,
    )

    assert result["answer"] == "ok"
    assert result["session_id"] == "new12345"
    assert service.calls == [("hello", None, "u1", None)]


@pytest.mark.asyncio
async def test_chat_api_rejects_blank_question_before_service_call():
    from api.chat import ChatRequest, chat

    service = FakeChatService()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(chat=service)))

    with pytest.raises(HTTPException) as exc_info:
        await chat(ChatRequest(question="   ", user_id="u1"), request)

    assert exc_info.value.status_code == 400
    assert service.calls == []
