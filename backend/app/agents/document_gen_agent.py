from langchain_core.prompts import ChatPromptTemplate
from app.agents.base_agent import BaseAgent
from app.config import settings

class DocumentGenAgent(BaseAgent):
    """Step 7: 文书生成 Agent"""

    def __init__(self):
        self.llm = None
        if settings.OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL_NAME,
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                    temperature=0.4
                )
            except ImportError:
                self.llm = None

    async def run(self, input_data: dict) -> dict:
        case_description = input_data.get("case_description", "")
        claims = input_data.get("claims", [])
        document_type = input_data.get("document_type", "仲裁申请书")

        if not self.llm:
            return {
                "content": self._get_template_document(document_type, case_description),
                "document_type": document_type
            }

        claims_text = "\n".join([f"- {c}" for c in claims]) if claims else "（无具体权益清单）"

        template = f"""作为劳动仲裁文书起草专家，根据以下案件信息生成{document_type}。

案件事实：
{case_description}

仲裁请求/权益清单：
{claims_text}

请生成一份完整、规范的{document_type}，包含：
1. 当事人信息
2. 仲裁请求事项
3. 事实与理由
4. 证据清单

注意：
- 使用正式的法律用语
- 金额计算精确
- 事实描述清晰准确

直接输出文书内容，不需要额外解释。"""

        try:
            result = await self.llm.ainvoke(template)
            return {
                "content": result.content if hasattr(result, 'content') else str(result),
                "document_type": document_type
            }
        except Exception as e:
            return {
                "content": self._get_template_document(document_type, case_description),
                "document_type": document_type
            }

    def _get_template_document(self, document_type: str, case_description: str) -> str:
        if document_type == "仲裁申请书":
            return f"""劳动人事争议仲裁申请书

申请人：__________（姓名）
身份证号：__________
联系电话：__________
地址：__________

被申请人：__________（单位名称）
法定代表人：__________
地址：__________

仲裁请求：
1. 请求被申请人支付拖欠工资 _______ 元；
2. 请求被申请人支付经济补偿金 _______ 元；
3. 其他请求：__________

事实与理由：
{case_description or '（此处填写案件事实）'}

此致
_______劳动人事争议仲裁委员会

申请人（签名）：__________
____年____月____日
"""
        return f"""劳动维权文书

案件类型：{document_type}

案件描述：
{case_description or '（案件描述待补充）'}

文书内容待通过AI生成完整版本。
"""