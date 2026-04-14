from langchain_core.tools import tool
from app.agents.base_agent import BaseAgent
from app.chains.retrieval_chain import RetrievalChain
from app.config import settings
import json

class CaseAnalysisAgent(BaseAgent):
    """Step 4: 案情分析 Agent (ReAct 模式)"""

    def __init__(self):
        self.llm = None
        if settings.OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL_NAME,
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                    temperature=0.3
                )
            except ImportError:
                self.llm = None
        try:
            self.retrieval_chain = RetrievalChain()
        except Exception:
            self.retrieval_chain = None
        self.tools = []

    async def run(self, input_data: dict) -> dict:
        answers = input_data.get("answers", [])
        case_text = self._build_case_text(answers)

        if not self.llm:
            # 无 LLM 时返回基础分析
            cause_codes = self._extract_cause_codes(answers)
            return {
                "case_description": case_text or "用户尚未提供详细案情描述",
                "cause_codes": cause_codes or ["A001"],
                "confidence": 0.5
            }

        # 使用 LLM 分析
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        template = """你是一名劳动法律师助理，帮助分析用户的劳动维权案件。

根据以下案情描述，分析并返回 JSON 格式结果：
{{"case_description": "规范的案件事实描述", "cause_codes": ["案由编码列表"], "confidence": 0.85}}

案情描述：
{case_text}

请直接返回 JSON，不要有其他内容。"""

        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm | StrOutputParser()

        try:
            result = await chain.ainvoke({"case_text": case_text})
            return self._parse_result(result)
        except Exception as e:
            return {
                "case_description": case_text,
                "cause_codes": [],
                "confidence": 0.0,
                "error": str(e)
            }

    def _build_case_text(self, answers: list) -> str:
        return "\n".join([
            f"问题: {a.get('question_id', '')}\n回答: {a.get('answer_value', '')}"
            for a in answers
        ])

    def _extract_cause_codes(self, answers: list) -> list:
        """从答案中提取案由编码"""
        codes = []
        for answer in answers:
            value = str(answer.get("answer_value", "")).lower()
            if "欠薪" in value or "工资" in value:
                codes.append("A001")
            elif "开除" in value or "解除" in value:
                codes.append("A002")
            elif "工伤" in value:
                codes.append("A003")
            elif "调岗" in value:
                codes.append("A004")
            elif "社保" in value or "保险" in value:
                codes.append("A005")
        return list(set(codes)) if codes else ["A001"]

    def _parse_result(self, result: str) -> dict:
        import re
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        return {"case_description": result, "cause_codes": [], "confidence": 0.5}