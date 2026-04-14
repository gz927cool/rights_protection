from app.agents.base_agent import BaseAgent
from app.config import settings
from langchain_qianwen import ChatQianwen
from langchain_core.prompts import ChatPromptTemplate
import json
import re


class ContextualAnalysisAgent(BaseAgent):
    """上下文分析 Agent — 步骤完成时调用，返回分析和建议"""

    def __init__(self):
        self.llm = None
        try:
            self.llm = ChatQianwen(
                model="qwen-plus",
                qianwen_api_key=settings.QWEN_API_KEY,
                temperature=0.3
            )
        except Exception:
            self.llm = None

    async def run(self, input_data: dict) -> dict:
        context_data = input_data.get("context_data", {})
        current_step = input_data.get("current_step", 1)

        if not self.llm:
            return {
                "analysis": "AI 服务暂时不可用，请稍后再试。",
                "suggestions": [],
                "case_summary": context_data.get("case_summary", "")
            }

        template = self._build_prompt_template(current_step)
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm

        result = await chain.ainvoke({
            "case_summary": context_data.get("case_summary", ""),
            "answers_this_step": json.dumps(context_data.get("answers_this_step", {}), ensure_ascii=False),
            "previous_steps_summary": json.dumps(context_data.get("previous_steps_summary", {}), ensure_ascii=False),
            "evidence_status": json.dumps(context_data.get("evidence_status", {}), ensure_ascii=False),
            "user_question": context_data.get("user_question") or "无",
            "step_label": context_data.get("step_label", "")
        })

        return self._parse_result(result)

    def _build_prompt_template(self, current_step: int) -> str:
        base = """你是一名劳动维权 AI 助手，正在帮助用户完成维权案件的填写。

当前步骤：{step_label}（第 {current_step} 步，共 9 步）

案件摘要：
{case_summary}

当前步骤用户填写：
{answers_this_step}

前置步骤摘要：
{previous_steps_summary}

证据状态：
{evidence_status}

{fact_sheet}

请分析以上信息，返回 JSON 格式：
{{
    "analysis": "对话式分析文本，用友好易懂的语言总结发现的问题和下一步建议",
    "suggestions": [
        {{
            "id": "sug_001",
            "type": "field_correction|missing_info|risk_alert|calculation",
            "field": "字段标识符",
            "fieldLabel": "字段中文名称",
            "suggestedValue": "建议填入的值",
            "confidence": 0.0-1.0,
            "reason": "为什么给出这个建议"
        }}
    ],
    "case_summary": "基于新信息更新的案件摘要"
}}

要求：
- analysis 应通俗易懂，用"您"称呼用户
- suggestions 仅在置信度 >= 0.7 时生成
- type: field_correction=字段修正, missing_info=补充信息, risk_alert=风险提示, calculation=金额计算
- 仅返回 JSON，不要有其他内容"""

        fact_sheets = {
            1: "【法律参考】拖欠工资：用人单位应按时足额支付劳动报酬，不得无故拖欠。",
            2: "【法律参考】经济补偿金：根据《劳动合同法》第47条，工作满1年支付1个月工资作为经济补偿。",
            3: "【法律参考】工龄计算：从入职之日起算，包括试用期。",
            4: "【法律参考】案由判定：需结合具体事实和法律依据综合判断。",
            5: "【法律参考】证据要求：劳动仲裁中证据必须真实、合法、与案件有关联。",
            6: "【法律参考】风险提示：时效风险（劳动仲裁1年时效）、证据风险、金额计算错误风险。",
        }

        fact_sheet = fact_sheets.get(current_step, "")
        return base.replace("{fact_sheet}", fact_sheet)

    def _parse_result(self, result) -> dict:
        output = result.content if hasattr(result, 'content') else str(result)
        try:
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    "analysis": parsed.get("analysis", ""),
                    "suggestions": parsed.get("suggestions", []),
                    "case_summary": parsed.get("case_summary", "")
                }
        except json.JSONDecodeError:
            pass
        return {"analysis": output, "suggestions": [], "case_summary": ""}