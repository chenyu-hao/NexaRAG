class FakeIngestion:
    def __init__(self):
        self.calls = []

    def add_document(self, text, source):
        self.calls.append(("add_document", text, source))
        return "document added"

    def add_file(self, path):
        self.calls.append(("add_file", path))
        return "file added"


class FakeRetriever:
    def __init__(self):
        self.calls = []

    def search(self, query, top_k=None):
        self.calls.append(("search", query, top_k))
        return [{"text": "answer context", "metadata": {"source": "a.txt"}}]

    def search_product(self, product_name, top_k=None):
        self.calls.append(("search_product", product_name, top_k))
        return [{"text": "product context"}]

    def search_troubleshoot(self, problem, top_k=None):
        self.calls.append(("search_troubleshoot", problem, top_k))
        return [{"text": "support context"}]

    def search_as_documents(self, query, top_k=None):
        self.calls.append(("search_as_documents", query, top_k))
        return []

    def sync_index(self):
        self.calls.append(("sync_index",))
        return 2


def test_rag_ingestion_chain_delegates_storage_flow():
    from rag.ingestion_chain import KnowledgeIngestionChain

    ingestion = FakeIngestion()
    chain = KnowledgeIngestionChain(ingestion)

    assert chain.add_document("text", "source.txt") == "document added"
    assert chain.add_file("source.txt") == "file added"
    assert ingestion.calls == [
        ("add_document", "text", "source.txt"),
        ("add_file", "source.txt"),
    ]


def test_rag_retrieval_chain_delegates_question_answer_search():
    from rag.retrieval_chain import QuestionAnswerRetrievalChain

    retriever = FakeRetriever()
    chain = QuestionAnswerRetrievalChain(retriever)

    assert chain.search("battery", top_k=3)[0]["text"] == "answer context"
    assert chain.search_product("Mate", top_k=2)[0]["text"] == "product context"
    assert chain.search_troubleshoot("charging", top_k=4)[0]["text"] == "support context"
    assert chain.sync_index() == 2

    assert retriever.calls == [
        ("search", "battery", 3),
        ("search_product", "Mate", 2),
        ("search_troubleshoot", "charging", 4),
        ("sync_index",),
    ]


def test_rag_evaluation_chain_computes_retrieval_metrics():
    from rag.evaluation_chain import RetrievalEvaluationChain

    chain = RetrievalEvaluationChain()
    metrics = chain.eval_retrieval(
        [
            {"metadata": {"source": "a.txt"}},
            {"metadata": {"source": "b.txt"}},
        ],
        ["b.txt", "c.txt"],
    )

    assert metrics == {"precision": 0.5, "recall": 0.5, "mrr": 0.5}
