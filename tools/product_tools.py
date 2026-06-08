from __future__ import annotations

from langchain_core.tools import StructuredTool

from tools.retrieval_tools import _format_results


def build_product_tools(knowledge_base) -> list:
    def compare_products(product_names: list[str]) -> str:
        """Compare multiple products by retrieving their knowledge records."""
        docs = []
        for name in product_names:
            docs.extend(knowledge_base.search_product(name, top_k=3))
        return _format_results(docs)

    def get_product_specs(product_name: str) -> str:
        """Get product specification information."""
        docs = knowledge_base.search_product(product_name, top_k=6)
        return _format_results(docs)

    def get_troubleshoot_guide(problem: str) -> str:
        """Get troubleshooting guidance for a product problem."""
        docs = knowledge_base.search_troubleshoot(problem, top_k=8)
        return _format_results(docs)

    return [
        StructuredTool.from_function(compare_products),
        StructuredTool.from_function(get_product_specs),
        StructuredTool.from_function(get_troubleshoot_guide),
    ]
