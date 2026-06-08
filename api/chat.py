"""对话 API"""
import base64
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from config import settings as config

router = APIRouter(prefix="/chat", tags=["对话"])


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None
    user_id: str = "default"


def _get_chat(request: Request):
    return request.app.state.chat


def _validate_question(question: str) -> str:
    normalized = question.strip()
    if not normalized:
        raise HTTPException(400, "问题不能为空")
    return normalized


def _validate_images(files: list[UploadFile]) -> list[str]:
    """校验图片并转为 base64 列表"""
    if len(files) > config.max_images_per_message:
        raise HTTPException(400, f"单次最多上传 {config.max_images_per_message} 张图片")
    result = []
    max_bytes = config.max_image_size_mb * 1024 * 1024
    for f in files:
        data = f.file.read()
        if len(data) > max_bytes:
            raise HTTPException(400, f"图片 {f.filename} 超过 {config.max_image_size_mb}MB 限制")
        b64 = base64.b64encode(data).decode("utf-8")
        # 拼接 data URI 前缀，DashScope 多模态 API 需要
        content_type = f.content_type or "image/jpeg"
        result.append(f"data:{content_type};base64,{b64}")
    return result


# ==================== 纯文本接口（保持不变，向后兼容）====================

@router.post("")
async def chat(req: ChatRequest, request: Request):
    chat_service = _get_chat(request)
    return await chat_service.chat(
        _validate_question(req.question),
        session_id=req.session_id,
        user_id=req.user_id,
    )


@router.post("/stream")
async def chat_stream(req: ChatRequest, request: Request):
    chat_service = _get_chat(request)
    question = _validate_question(req.question)

    async def generate():
        async for token in chat_service.chat_stream(
            question,
            session_id=req.session_id,
            user_id=req.user_id,
        ):
            yield token

    return StreamingResponse(generate(), media_type="text/plain")


# ==================== 图片对话接口（multipart/form-data）====================

@router.post("/image")
async def chat_image(
    question: str = Form(...),
    session_id: str | None = Form(None),
    user_id: str = Form("default"),
    images: list[UploadFile] = File(default=[]),
    request: Request = None,
):
    question = _validate_question(question)
    # 校验并转 base64
    image_b64_list = _validate_images(images) if images else []
    chat_service = _get_chat(request)
    return await chat_service.chat(
        question,
        session_id=session_id,
        user_id=user_id,
        images=image_b64_list,
    )


@router.post("/image/stream")
async def chat_image_stream(
    question: str = Form(...),
    session_id: str | None = Form(None),
    user_id: str = Form("default"),
    images: list[UploadFile] = File(default=[]),
    request: Request = None,
):
    question = _validate_question(question)
    image_b64_list = _validate_images(images) if images else []
    chat_service = _get_chat(request)

    async def generate():
        async for token in chat_service.chat_stream(
            question,
            session_id=session_id,
            user_id=user_id,
            images=image_b64_list,
        ):
            yield token

    return StreamingResponse(generate(), media_type="text/plain")


# ==================== 会话管理 ====================

@router.post("/{session_id}/end")
async def end_session(session_id: str, request: Request, user_id: str = "default"):
    chat_service = _get_chat(request)
    result = await chat_service.end_session(session_id, user_id=user_id)
    if result.get("error") == "not_found":
        raise HTTPException(404, "会话不存在")
    return result


@router.get("/{session_id}/history")
async def get_history(
    session_id: str, request: Request, user_id: str = "default",
    limit: int = 0, offset: int = 0,
):
    chat_service = _get_chat(request)
    result = chat_service.get_history(
        session_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    if result is None:
        raise HTTPException(404, "会话不存在")
    return result
