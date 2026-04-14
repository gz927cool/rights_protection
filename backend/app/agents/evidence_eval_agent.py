from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.agents.base_agent import BaseAgent
from app.config import settings

class EvidenceEvalAgent(BaseAgent):
    """Step 5: 证据审核 Agent (Chain 模式)"""

    def __init__(self):
        self.llm = None
        self.chain = None
        if settings.OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL_NAME,
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                    temperature=0.1
                )
                self._setup_chain()
            except ImportError:
                self.llm = None

    def _setup_chain(self):
        template = """你是一名证据审核专家，评估用户提交的证据是否充分。

证据信息：
- 证据名称: {evidence_name}
- 证据类型: {evidence_type}
- 用户备注: {note}

案由: {cause_codes}

请评估并返回 JSON：
{{"is_valid": true/false, "clarity_score": 0-100, "relevance_score": 0-100, "completeness_score": 0-100, "issues": ["问题列表"], "suggestions": ["改进建议"]}}"""

        self.prompt = ChatPromptTemplate.from_template(template)
        if self.llm:
            self.chain = self.prompt | self.llm | JsonOutputParser()

    async def run(self, input_data: dict) -> dict:
        if not self.llm or not self.chain:
            return {
                "is_valid": True,
                "clarity_score": 75,
                "relevance_score": 80,
                "completeness_score": 70,
                "issues": [],
                "suggestions": ["AI模型未配置，请手动确认证据完整性"]
            }

        try:
            result = await self.chain.ainvoke({
                "evidence_name": input_data.get("name", ""),
                "evidence_type": input_data.get("type", ""),
                "note": input_data.get("note", ""),
                "cause_codes": ",".join(input_data.get("cause_codes", []))
            })
            return result
        except Exception as e:
            return {
                "is_valid": True,
                "clarity_score": 75,
                "relevance_score": 80,
                "completeness_score": 70,
                "issues": [str(e)],
                "suggestions": ["请稍后重试"]
            }