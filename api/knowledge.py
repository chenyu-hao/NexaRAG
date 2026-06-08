"""知识库 API"""
from fastapi import APIRouter, UploadFile, File, Request

router = APIRouter(prefix="/knowledge", tags=["知识库"])


def _get_knowledge(request: Request):
    return request.app.state.knowledge


@router.post("/upload")
async def upload(file: UploadFile = File(...), request: Request = None):
    knowledge = _get_knowledge(request)
    content = (await file.read()).decode("utf-8")
    result = knowledge.add_document(content, file.filename)
    knowledge.sync_index()
    return {"msg": result, "filename": file.filename}
