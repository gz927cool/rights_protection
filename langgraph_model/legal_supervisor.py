from typing import Dict, TypedDict, List, Tuple, Optional, Annotated
from langgraph.graph import StateGraph, END, START
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
# from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
from typing_extensions import TypedDict, Literal
import json
import os
import uuid
from langchain_core.output_parsers import JsonOutputParser
from json_repair import repair_json
from langgraph_model.prompts import ANSWERER_PROMPT,DETAILER_PROMPT,ADVISOR_PROMPT,PROCESS_SELECTION_PROMPT,LEGAL_SERVICES,SUMMARIZER_PROMPT
from langgraph_model.state import AgentState,InputState
from langgraph_model.load_cfg import OPENAI_API_KEY,MODEL_NAME,BASE_URL
# 创建不同角色的模型实例
model = ChatOpenAI(model=MODEL_NAME , api_key=OPENAI_API_KEY,base_url=BASE_URL, temperature=0, max_tokens=4096)

    
"""
Personal Assistant Supervisor Example

This example demonstrates the tool calling pattern for multi-agent systems.
A supervisor agent coordinates specialized sub-agents (calendar and email)
that are wrapped as tools.
"""

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool, ToolRuntime

# ============================================================================
# Step 1: Define low-level API tools (stubbed)
# ============================================================================


# ============================================================================
# Step 2: Create specialized sub-agents
# ============================================================================


answerer_agent = create_agent(
    model,
    system_prompt=(
"""## 角色定位

你是宿迁工会的劳动争议咨询团队的助手，负责专为一线职工提供法律指引。
你的语气：开口亲切、有温度，进入分析后切换为专业清晰。
你的目标：帮职工看清自己的情况、明确自己的权利。

## 第一步：案由定性（信息充足后，显性告知）

根据用户描述，从以下常见案由类型中判断并明确告知：

  ▸ 追索欠薪（基本工资 / 加班工资 / 绩效奖金）
  ▸ 违法解除劳动合同（赔偿金 N×2）
  ▸ 未签书面劳动合同二倍工资
  ▸ 解除/终止劳动合同经济补偿金（N）
  ▸ 工伤保险待遇纠纷
  ▸ 确认劳动关系纠纷
  ▸ 其他（说明）

告知格式示例：
  "根据描述的情况，遇到的属于【违法解除劳动合同纠纷】，
   您有权要求公司支付赔偿金（即经济补偿金的2倍）。"

若涉及多个案由，逐一列出并简要说明各自权利。

## 第二步：初步法律解答

在案由定性后，给出精准的法律解答，包含：

  1. 核心权利是什么（能主张什么）
  2. 相关法律依据（引用具体条款名称即可，无需全文）
  3. 重要的时效提示（如：劳动仲裁时效为 1 年）

语言要求：
  - 专业但不晦涩，避免大段法条堆砌，友好流畅的交流风格。
  - 金额计算可给出公式，例如：
    "经济补偿 = 工作年限 × 月平均工资，您工作 N 年，
     对应 N 个月工资的赔偿"
  - 如遇本地特殊规定（如宿迁地区二倍工资时效计算口径），
    注明"建议向工会法律援助人员确认"

## 注意事项
  - 不要主动推荐具体服务（由 advisor 负责）
  - 不要一次性输出所有情形（由 detailer 负责）"""
    )
)

summarizer_agent = create_agent(
    model,
    system_prompt=(
        SUMMARIZER_PROMPT
    )
)
detailer_agent = create_agent(
    model,
    system_prompt=(
        DETAILER_PROMPT
    )
)
advisor_agent = create_agent(
    model,
    system_prompt=(
        ADVISOR_PROMPT
    )
)

# ============================================================================
# Step 3: Wrap sub-agents as tools for the supervisor
# ============================================================================

@tool
def answerer(runtime: ToolRuntime) -> str:
    """对用户的咨询进行初步回答，检查信息完整性；向用户追问；提供初步方案。
    """
    result = answerer_agent.invoke({
        "messages": runtime.state["messages"]
    })
    return result["messages"][-1].text


@tool
def summarizer(runtime: ToolRuntime) -> str:
    """对用户的案情进行总结
    """
    result = summarizer_agent.invoke({
        "messages": runtime.state["messages"]
    })
    return result["messages"][-1].text

@tool
def detailer(runtime: ToolRuntime) -> str:
    """将当前任务交给detailer处理，推理用户可能遇到的情况。
    """
    result = detailer_agent.invoke({
        "messages": runtime.state["messages"]
    })
    return result["messages"][-1].text


@tool
def advisor(runtime: ToolRuntime) -> str:
    """将当前任务交给advisor处理，根据用户确认的案情情形，为其规划最适合的行动路线图。
    """
    result = advisor_agent.invoke({
        "messages": runtime.state["messages"]
    })
    return result["messages"][-1].text


# ============================================================================
# Step 4: Create the supervisor agent
# ============================================================================

supervisor_agent = create_agent(
    model,
    tools=[answerer, summarizer, detailer, advisor],
    checkpointer=InMemorySaver(),
    system_prompt=(
        # PROCESS_SELECTION_PROMPT
"""你是宿迁工会劳动争议咨询团队的协调成员。
你的职责是：根据当前对话状态，简明扼要的追问信息；总结性地回复用户；或将任务分配给团队其他成员进行专业回复。

## 标准流程
1. 若用户描述中缺少以下关键信息，在正式解答前先友好追问：
必问项（缺一不行）：
  - 当前在职状态（在职/离职）
  - 离职时间（如已离职）
  - 是否签过书面劳动合同
  - 争议的核心（欠薪、被辞退、未签合同、其他）
选问项（视情形追问）：
  - 在这家公司工作时间
  - 欠薪或赔偿的大致金额
  - 事情发生在时间
追问时，每次只询问 1~2 个最关键的问题，不要一次列出所有问题。

2. [answerer]  负责进行案由定性并给出初步法律解答：
   - 如果用户提问时缺乏关键信息，先进行追问，待用户补充信息后再提交给[answerer]来为用户进行初步解答。
   - 如果用户提问时提供信息相对完善，直接移交[answerer]处理。
   - 当用户就具体情形或行动路线进行追问时，会话移交给[answerer]继续解答。

3. [detailer] 负责推演用户可能遇到的案情情形，并为每种情形提供证据攻略清单。
   -在 answerer 完成初步解答后执行
   -当detailer提供了多种情形后，需要用户确认所属情形。

4. [advisor]  负责根据用户确认的案情情形，为其规划最适合的行动路线图
  - 用户确认所属情形后，将会话移交给[advisor]处理。
  - 当提供了可能的途径后，需要用户确认采用何种途径。

5. [summarizer] 
  - 用户明确表示"生成文书"/"帮我写申请书"/"总结"启动
  - 用户请求总结或需要案情概述时启动。
  - 用户确认采用何种途径后，将会话移交给[summarizer]进行总结。


## 路由优先级规则
- 用户首次提问
    → 判定是否提供的关键信息
        if:是 → 让answerer进行初步解答
        if:否 → 直接追问
- answerer 完成初步解答后 → 转到 detailer 进行可能情形分析
- 用户选择情形后 → advisor
- 对话中存在情形和路线图后，用户追问细节 → answerer
- 用户说"帮我写申请书/文书/仲裁书" OR 用户说"总结一下/帮我整理" 
    → summarizer
- summarizer 编写了文书内容 
    → 一句话简要提示文书填写注意事项然后结束。
- 当需要用户输入或选择时，则直接和用户交互，不经过其他成员。
- 当需要用户输入时，根据当前是否有相关提示，添加提示或直接等待输入。

## 注意事项：
    客户能够看到团队每个成员的回复，**一定不能**直接重复其成员的回答。
    注意自己的能力边界，你只能文本回复用户,暂时无法提供完全填好的Word版文件
"""
    )
)

# ============================================================================
# Step 5: Use the supervisor
# ============================================================================

if __name__ == "__main__":
    # Example: User request requiring both calendar and email coordination
    user_request = "公司上周突然叫我走人，说我不符合岗位要求，也没给我任何书面通知，工作了两年半，一分补偿都没有，我应该能拿赔偿吧"

    print("User Request:", user_request)
    print("\n" + "="*80 + "\n")

    config = {
        "configurable": {"thread_id": 111},
        "recursion_limit": 300
    }
    for step in supervisor_agent.stream(
        {"messages": [{"role": "user", "content": user_request}]},
        config=config
    ):
        for update in step.values():
            for message in update.get("messages", []):
                message.pretty_print()