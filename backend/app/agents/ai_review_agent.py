from langchain_core.prompts import ChatPromptTemplate
from app.agents.base_agent import BaseAgent
from app.config import settings

class AIReviewAgent(BaseAgent):
    """Step 9: AI 复核 Agent"""

    def __init__(self):
        self.llm = None
        if settings.OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL_NAME,
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                    temperature=0.5
                )
            except ImportError:
                self.llm = None

    async def run(self, input_data: dict) -> dict:
        case_data = input_data.get("case_data", {})
        user_question = input_data.get("user_question", "请复核我的案件")

        if not self.llm:
            return {
                "review": self._get_basic_review(case_data, user_question)
            }

        template = """你是劳动法律专家，请复核用户的劳动维权案件。

案件信息：
{case_data}

用户问题：{question}

请提供专业的复核意见，包括：
1. 案件事实是否清晰
2. 案由选择是否正确
3. 证据是否充分
4. 仲裁请求是否合理
5. 其他建议"""

        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm

        try:
            result = await chain.ainvoke({
                "case_data": str(case_data),
                "question": user_question
            })
            return {"review": result.content if hasattr(result, 'content') else str(result)}
        except Exception as e:
            return {"review": self._get_basic_review(case_data, user_question)}

    def _get_basic_review(self, case_data: dict, user_question: str) -> str:
        return f"""【AI复核意见】

您好！感谢您使用工会劳动维权AI引导系统。

当前系统AI模型暂未配置完整功能，建议您：

1. 完成所有步骤的案情填写
2. 准备好相关证据材料
3. 如有需要，可联系当地工会或法律援助中心

您的问题：{user_question}

建议：
- 劳动仲裁时效为一年，从知道或应当知道权利被侵害之日起计算
- 保留好所有与工作相关的证据，包括工资条、劳动合同、考勤记录等
- 如有需要，可向当地法律援助中心申请免费法律咨询

如需更详细的帮助，请联系工会工作人员或专业律师。
"""