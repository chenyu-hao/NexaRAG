class FakeIngestion:
    def __init__(self):
        self.added_documents = []
        self.added_files = []

    def add_document(self, text, source):
        self.added_documents.append((text, source))
        return "[success] indexed document"

    def add_file(self, path):
        self.added_files.append(path)
        return "[success] indexed file"


class FakeRetriever:
    def __init__(self):
        self.calls = []

    def search(self, query, top_k=None):
        self.calls.append(("search", query, top_k))
        return [{"text": "battery info", "metadata": {"source": "phone.txt"}}]

    def search_product(self, product_name, top_k=None):
        self.calls.append(("search_product", product_name, top_k))
        return [{"text": "product info", "metadata": {"source": "product.txt"}}]

    def search_troubleshoot(self, problem, top_k=None):
        self.calls.append(("search_troubleshoot", problem, top_k))
        return [{"text": "troubleshoot info", "metadata": {"source": "support.txt"}}]

    def sync_index(self):
        self.calls.append(("sync_index",))
        return 3


def test_knowledge_base_delegates_document_ingestion_and_search():
    from rag.knowledge_base import KnowledgeBase

    ingestion = FakeIngestion()
    retriever = FakeRetriever()
    kb = KnowledgeBase(ingestion=ingestion, retriever=retriever)

    assert kb.add_document("battery capacity", "phone.txt") == "[success] indexed document"
    assert ingestion.added_documents == [("battery capacity", "phone.txt")]

    results = kb.search("battery", top_k=2)

    assert results == [{"text": "battery info", "metadata": {"source": "phone.txt"}}]
    assert retriever.calls == [("search", "battery", 2)]


def test_knowledge_base_exposes_product_troubleshoot_and_sync_methods():
    from rag.knowledge_base import KnowledgeBase

    retriever = FakeRetriever()
    kb = KnowledgeBase(ingestion=FakeIngestion(), retriever=retriever)

    assert kb.search_product("Mate 70 Pro", top_k=4)[0]["text"] == "product info"
    assert kb.search_troubleshoot("charging issue", top_k=5)[0]["text"] == "troubleshoot info"
    assert kb.sync_index() == 3

    assert retriever.calls == [
        ("search_product", "Mate 70 Pro", 4),
        ("search_troubleshoot", "charging issue", 5),
        ("sync_index",),
    ]
