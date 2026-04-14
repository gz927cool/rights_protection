from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.agents.base_agent import BaseAgent
from app.config import settings
import json

class RiskAssessAgent(BaseAgent):
    """Step 6: 风险评估 Agent"""

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

    async def run(self, input_data: dict) -> dict:
        case_description = input_data.get("case_description", "")
        cause_codes = input_data.get("cause_codes", [])
        evidence_status = input_data.get("evidence_status", {})

        if not self.llm:
            # 返回基础风险评估
            risk_points = self._get_basic_risks(cause_codes, evidence_status)
            overall = self._calculate_overall_level(risk_points)
            return {
                "risk_points": risk_points,
                "overall_level": overall,
                "suggestions": ["建议咨询专业律师获取准确风险评估"]
            }

        template = """作为劳动维权风险分析师，分析以下案件的风险等级。

案件描述：
{case_description}

案由：{cause_codes}

证据状态：
{evidence_status}

请识别风险并返回 JSON：
{{"risk_points": [{{"type": "风险类型", "level": "高/中/低", "description": "描述", "reason": "原因"}}], "overall_level": "高/中/低", "suggestions": ["建议"]}}"""

        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm | StrOutputParser()

        try:
            result = await chain.ainvoke({
                "case_description": case_description,
                "cause_codes": ",".join(cause_codes),
                "evidence_status": str(evidence_status)
            })
            return self._parse_result(result)
        except Exception as e:
            risk_points = self._get_basic_risks(cause_codes, evidence_status)
            return {
                "risk_points": risk_points,
                "overall_level": "中",
                "suggestions": [f"评估失败: {str(e)}"]
            }

    def _get_basic_risks(self, cause_codes: list, evidence_status: dict) -> list:
        risks = []
        type_c = evidence_status.get("type_c", 0)
        if type_c > 0:
            risks.append({
                "type": "证据风险",
                "level": "高",
                "description": f"存在 {type_c} 项无法取得的证据",
                "reason": "缺少关键证据可能影响案件胜诉"
            })
        if not cause_codes:
            risks.append({
                "type": "定性风险",
                "level": "中",
                "description": "案由尚未确定",
                "reason": "需要先明确案由才能进一步分析"
            })
        risks.extend([
            {"type": "时效风险", "level": "中", "description": "注意劳动仲裁时效", "reason": "劳动仲裁时效为一年"},
            {"type": "举证风险", "level": "中", "description": "注意证据保全", "reason": "电子证据容易丢失"}
        ])
        return risks

    def _calculate_overall_level(self, risk_points: list) -> str:
        if any(r.get("level") == "高" for r in risk_points):
            return "高"
        return "中"

    def _parse_result(self, result: str) -> dict:
        import re
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        return {"risk_points": [], "overall_level": "中", "suggestions": []}