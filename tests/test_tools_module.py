class FakeKnowledgeBase:
    def __init__(self):
        self.calls = []

    def search_as_documents(self, query, top_k=None):
        self.calls.append(("search_as_documents", query, top_k))
        return [
            type(
                "Doc",
                (),
                {
                    "page_content": "battery capacity 5000mAh",
                    "metadata": {"source": "phone.txt"},
                },
            )()
        ]

    def search_product(self, product_name, top_k=None):
        self.calls.append(("search_product", product_name, top_k))
        return [{"text": "product specs", "metadata": {"source": "product.txt"}}]

    def search_troubleshoot(self, problem, top_k=None):
        self.calls.append(("search_troubleshoot", problem, top_k))
        return [{"text": "troubleshoot steps", "metadata": {"source": "support.txt"}}]


def test_retrieval_tools_use_injected_knowledge_base():
    from tools.retrieval_tools import build_retrieval_tools

    knowledge = FakeKnowledgeBase()
    tool_map = {tool.name: tool for tool in build_retrieval_tools(knowledge)}

    result = tool_map["search_knowledge"].invoke({"query": "battery", "top_k": 2})

    assert "battery capacity 5000mAh" in result
    assert "[phone.txt]" in result
    assert knowledge.calls == [("search_as_documents", "battery", 2)]


def test_product_tools_use_injected_knowledge_base():
    from tools.product_tools import build_product_tools

    knowledge = FakeKnowledgeBase()
    tool_map = {tool.name: tool for tool in build_product_tools(knowledge)}

    compare = tool_map["compare_products"].invoke({"product_names": ["Mate 70 Pro"]})
    troubleshoot = tool_map["get_troubleshoot_guide"].invoke({"problem": "charging"})

    assert "product specs" in compare
    assert "troubleshoot steps" in troubleshoot
    assert knowledge.calls == [
        ("search_product", "Mate 70 Pro", 3),
        ("search_troubleshoot", "charging", 8),
    ]


def test_tool_registry_returns_registered_toolsets():
    from tools.registry import ToolRegistry
    from tools.retrieval_tools import build_retrieval_tools

    registry = ToolRegistry()
    registry.register_many("retrieval", build_retrieval_tools(FakeKnowledgeBase()))

    tools = registry.get_toolset("retrieval")

    assert [tool.name for tool in tools] == [
        "search_knowledge",
        "search_product_knowledge",
        "search_troubleshoot_docs",
    ]
