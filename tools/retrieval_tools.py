from __future__ import annotations

from langchain_core.tools import StructuredTool


def _format_result(item) -> str:
    if hasattr(item, "page_content"):
        source = getattr(item, "metadata", {}).get("source", "")
        return f"[{source}] {item.page_content}"
    source = item.get("metadata", {}).get("source", "")
    text = item.get("text", "")
    return f"[{source}] {text}"


def _format_results(items) -> str:
    if not items:
        return "未找到相关信息"
    return "\n\n".join(_format_result(item) for item in items)


def build_retrieval_tools(knowledge_base) -> list:
    def search_knowledge(query: str, top_k: int = 6) -> str:
        """Search the product knowledge base for relevant information."""
        docs = knowledge_base.search_as_documents(query, top_k=top_k)
        return _format_results(docs)

    def search_product_knowledge(product_name: str, top_k: int = 6) -> str:
        """Search knowledge for a specific product name."""
        docs = knowledge_base.search_product(product_name, top_k=top_k)
        return _format_results(docs)

    def search_troubleshoot_docs(problem: str, top_k: int = 8) -> str:
        """Search troubleshooting documents for a user problem."""
        docs = knowledge_base.search_troubleshoot(problem, top_k=top_k)
        return _format_results(docs)

    return [
        StructuredTool.from_function(search_knowledge),
        StructuredTool.from_function(search_product_knowledge),
        StructuredTool.from_function(search_troubleshoot_docs),
    ]
