from __future__ import annotations

from tools.product_tools import build_product_tools
from tools.retrieval_tools import build_retrieval_tools


def build_customer_service_toolset(knowledge_base) -> list:
    return [
        *build_retrieval_tools(knowledge_base),
        *build_product_tools(knowledge_base),
    ]
