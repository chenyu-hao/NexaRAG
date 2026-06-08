from types import SimpleNamespace

import pytest


class FakeKnowledgeBase:
    def __init__(self):
        self.added = []
        self.synced = False

    def add_document(self, text, source):
        self.added.append((text, source))
        return "[success] loaded 1 chunks"

    def sync_index(self):
        self.synced = True
        return 1


class FakeUploadFile:
    filename = "phone.txt"

    async def read(self):
        return "battery info".encode("utf-8")


@pytest.mark.asyncio
async def test_knowledge_upload_uses_knowledge_base_without_rag_state():
    from api.knowledge import upload

    knowledge = FakeKnowledgeBase()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(knowledge=knowledge)))

    result = await upload(file=FakeUploadFile(), request=request)

    assert result == {"msg": "[success] loaded 1 chunks", "filename": "phone.txt"}
    assert knowledge.added == [("battery info", "phone.txt")]
    assert knowledge.synced is True
