from __future__ import annotations

import json
import logging
import os
from datetime import datetime

from config import settings as config

logger = logging.getLogger(__name__)

EVAL_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "qa_pairs",
)


class RetrievalEvaluationChain:
    """Evaluate retrieval recall and answer quality for the RAG module."""

    def __init__(self):
        self._judge_llm = None
        self.results = []

    def _get_judge_llm(self):
        if self._judge_llm is None:
            from langchain_community.chat_models import ChatTongyi

            self._judge_llm = ChatTongyi(
                model=config.chat_model,
                dashscope_api_key=config.dashscope_api_key,
                temperature=0,
            )
        return self._judge_llm

    async def _get_judge_response(self, prompt: str) -> str:
        llm = self._get_judge_llm()
        response = await llm.ainvoke(prompt)
        return response.content.strip()

    def load_test_data(self, filepath: str = None) -> list[dict]:
        filepath = filepath or os.path.join(EVAL_DATA_DIR, "test_qa.json")
        if not os.path.exists(filepath):
            logger.warning("Evaluation data does not exist: %s", filepath)
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def eval_retrieval(self, retrieved_docs: list[dict], expected_sources: list[str]) -> dict:
        if not retrieved_docs or not expected_sources:
            return {"precision": 0, "recall": 0, "mrr": 0}

        retrieved_sources = []
        for doc in retrieved_docs:
            source = doc.get("metadata", {}).get("source", "")
            if source:
                retrieved_sources.append(source)

        relevant_retrieved = sum(1 for source in retrieved_sources if source in expected_sources)
        precision = relevant_retrieved / len(retrieved_sources) if retrieved_sources else 0
        recalled = sum(1 for source in expected_sources if source in retrieved_sources)
        recall = recalled / len(expected_sources) if expected_sources else 0

        mrr = 0
        for i, source in enumerate(retrieved_sources):
            if source in expected_sources:
                mrr = 1.0 / (i + 1)
                break

        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "mrr": round(mrr, 4),
        }

    async def eval_faithfulness(self, question: str, answer: str, context: str) -> dict:
        prompt = f"""评估以下回答是否忠实于提供的参考资料。

问题：{question}

参考资料：
{context}

回答：
{answer}

请按以下标准打分（1-5分）：
- 5分：完全基于参考资料，无任何编造
- 4分：大部分基于参考资料，有少量合理推断
- 3分：部分基于参考资料，部分编造
- 2分：少量基于参考资料，大部分编造
- 1分：完全编造，与参考资料无关

严格按JSON格式输出：{{"score": 分数, "reason": "原因"}}"""

        try:
            response = await self._get_judge_response(prompt)
            return self._parse_json(response, {"score": 0, "reason": "解析失败"})
        except Exception as e:
            return {"score": 0, "reason": f"评估失败: {e}"}

    async def eval_answer_relevance(self, question: str, answer: str) -> dict:
        prompt = f"""评估以下回答是否与问题相关。

问题：{question}
回答：{answer}

评分标准（1-5分）：
- 5分：完全回答了问题，信息准确有用
- 4分：基本回答了问题，有少量无关信息
- 3分：部分回答了问题，但不够完整
- 2分：与问题相关但没有实质回答
- 1分：完全答非所问

严格按JSON格式输出：{{"score": 分数, "reason": "原因"}}"""

        try:
            response = await self._get_judge_response(prompt)
            return self._parse_json(response, {"score": 0, "reason": "解析失败"})
        except Exception as e:
            return {"score": 0, "reason": f"评估失败: {e}"}

    async def run_evaluation(self, answer_service, test_data: list[dict] = None) -> dict:
        test_data = test_data or self.load_test_data()
        if not test_data:
            return {"error": "无测试数据"}

        results = []
        for i, case in enumerate(test_data):
            question = case["question"]
            expected_answer = case.get("answer", "")

            logger.info("Evaluating [%d/%d]: %s...", i + 1, len(test_data), question[:30])

            result = await answer_service.chat(question, user_id="eval_user")
            actual_answer = result["answer"]
            context = result.get("context", "")
            intent = result.get("intent", {})

            retrieval_score = {
                "context_length": len(context),
                "intent": intent.get("intent", ""),
            }
            faithfulness = await self.eval_faithfulness(
                question,
                actual_answer,
                context if context else "无检索上下文",
            )
            relevance = await self.eval_answer_relevance(question, actual_answer)

            results.append({
                "question": question,
                "expected_answer": expected_answer,
                "actual_answer": actual_answer,
                "retrieval": retrieval_score,
                "faithfulness": faithfulness,
                "relevance": relevance,
                "intent": intent,
            })

        report = self._generate_report(results)
        self.results = results
        return report

    def _generate_report(self, results: list[dict]) -> dict:
        faith_scores = [
            r["faithfulness"]["score"]
            for r in results
            if r["faithfulness"]["score"] > 0
        ]
        relev_scores = [
            r["relevance"]["score"]
            for r in results
            if r["relevance"]["score"] > 0
        ]

        report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_cases": len(results),
            "metrics": {
                "faithfulness_avg": round(sum(faith_scores) / len(faith_scores), 2) if faith_scores else 0,
                "relevance_avg": round(sum(relev_scores) / len(relev_scores), 2) if relev_scores else 0,
            },
            "intent_distribution": {},
            "details": results,
        }

        for result in results:
            intent = result["intent"].get("intent", "")
            report["intent_distribution"][intent] = report["intent_distribution"].get(intent, 0) + 1

        return report

    @staticmethod
    def _parse_json(text: str, default: dict) -> dict:
        try:
            return json.loads(text)
        except Exception:
            import re
            match = re.search(r"\{[^}]+\}", text)
            return json.loads(match.group()) if match else default

    def save_report(self, report: dict, filepath: str = None):
        filepath = filepath or os.path.join(
            EVAL_DATA_DIR,
            f"eval_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("Evaluation report saved: %s", filepath)


RAGEvaluator = RetrievalEvaluationChain
