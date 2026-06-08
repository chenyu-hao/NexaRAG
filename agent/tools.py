"""Compatibility exports for legacy agent graph imports."""

from rag.knowledge_base import KnowledgeBase
from tools.product_tools import build_product_tools
from tools.retrieval_tools import build_retrieval_tools

_knowledge_base = KnowledgeBase()
_tool_map = {
    tool.name: tool
    for tool in [
        *build_retrieval_tools(_knowledge_base),
        *build_product_tools(_knowledge_base),
    ]
}

search_knowledge = _tool_map["search_knowledge"]
compare_products = _tool_map["compare_products"]
get_troubleshoot_guide = _tool_map["get_troubleshoot_guide"]
