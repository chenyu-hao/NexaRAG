def test_reranker_skips_dashscope_when_no_model(monkeypatch):
    import dashscope
    from config import settings as config
    from rag.reranker import Reranker

    monkeypatch.setattr(config, "rerank_model", "")

    called = {"value": False}

    def fail_if_called(*args, **kwargs):
        called["value"] = True
        raise AssertionError("TextReRank should not be called when rerank_model is empty")

    monkeypatch.setattr(dashscope.TextReRank, "call", fail_if_called)

    documents = [
        {"text": "first", "metadata": {"source": "a.txt"}},
        {"text": "second", "metadata": {"source": "b.txt"}},
    ]

    assert Reranker().rerank("query", documents, top_k=1) == documents[:1]
    assert called["value"] is False
