"""回答质量验证"""
import json, re, logging
from langchain_community.chat_models import ChatTongyi
from config import settings as config

logger = logging.getLogger(__name__)


class AnswerVerifier:
    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            self._llm = ChatTongyi(model=config.classifier_model, dashscope_api_key=config.dashscope_api_key, temperature=0)
        return self._llm

    def verify(self, question: str, answer: str, context: str) -> dict:
        prompt = self._build_prompt(question, answer, context)
        try:
            response = self._get_llm().invoke(prompt).content.strip()
            result = self._parse_response(response)
            return self._apply_numeric_grounding(result, answer, context)
        except Exception as e:
            logger.error("验证失败: %s", e)
            return {"pass": True, "score": 3, "reason": str(e)}

    async def averify(self, question: str, answer: str, context: str, llm=None) -> dict:
        prompt = self._build_prompt(question, answer, context)
        try:
            model = llm or self._get_llm()
            response = (await model.ainvoke(prompt)).content.strip()
            result = self._parse_response(response)
            return self._apply_numeric_grounding(result, answer, context)
        except Exception as e:
            logger.error("验证失败: %s", e)
            return {"pass": True, "score": 3, "reason": str(e)}

    @staticmethod
    def _build_prompt(question: str, answer: str, context: str) -> str:
        return (
            "验证回答质量。标准：相关性、忠实性、完整性。"
            'JSON输出：{"pass":true,"score":4,"reason":"原因","suggestion":"建议"}'
            f"\n\n问题：{question}\n参考资料：{context[:800]}\n回答：{answer}"
        )

    @staticmethod
    def _parse_response(response: str) -> dict:
        try:
            return json.loads(response)
        except Exception:
            m = re.search(r"\{[^}]+\}", response)
            return json.loads(m.group()) if m else {"pass": True, "score": 3}

    @staticmethod
    def _numeric_claims(text: str) -> list[str]:
        unit_words = (
            r"(?:mAh|mah|W|w|℃|°C|C|分钟|分|min|mins|minute|minutes|小时|h|"
            r"%|元|GB|TB|MB|Hz|英寸|inch|inches|MP|倍)"
        )
        pattern = re.compile(
            rf"(?<![\w.])(\d+(?:\.\d+)?)(?:\s*[~\-–—至到]\s*(\d+(?:\.\d+)?))?\s*{unit_words}",
            re.IGNORECASE,
        )
        claims: list[str] = []
        for match in pattern.finditer(text):
            claims.append(match.group(1))
            if match.group(2):
                claims.append(match.group(2))
        return claims

    @classmethod
    def _apply_numeric_grounding(cls, result: dict, answer: str, context: str) -> dict:
        answer_numbers = cls._numeric_claims(answer)
        if not answer_numbers:
            return result
        context_numbers = set(cls._numeric_claims(context))
        unsupported = [number for number in answer_numbers if number not in context_numbers]
        if not unsupported:
            return result
        grounded = dict(result)
        grounded["pass"] = False
        grounded["score"] = min(int(grounded.get("score", 3) or 3), 2)
        grounded["unsupported_numbers"] = sorted(set(unsupported), key=unsupported.index)
        reason = grounded.get("reason", "")
        suffix = f"回答包含参考资料未支撑的数字: {', '.join(grounded['unsupported_numbers'])}"
        grounded["reason"] = f"{reason}；{suffix}" if reason else suffix
        grounded.setdefault("suggestion", "删除或改写没有资料出处的数字。")
        return grounded
