"""
九步劳动争议咨询系统 - LangGraph 实现

Phase 4 重构版：
- 所有工具用 @tool 装饰器定义，不再用文本 JSON 解析
- Node 内用 model.bind_tools() 循环处理工具调用
- 路由仍由 current_step 驱动（_route_to_next 保持不变）
"""
import json
from typing import Annotated, Dict, List, Literal, Optional, Any
from datetime import datetime
from operator import add as messages_add
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langgraph.errors import ParentCommand
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent

from langgraph_model.load_cfg import OPENAI_API_KEY, MODEL_NAME, BASE_URL
from langgraph_model.consultation_state import (
    ConsultationState,
    ConsultationInput,
    StepData,
    FileRef,
    STEP_NAMES,
    STEP_DISPLAY_NAMES,
    get_dirty_range,
    create_initial_state,
    get_evidence_checklist,
    get_evidence_guidance,
    evaluate_evidence_completeness,
)
from langgraph_model.prompts import STEP_PROMPTS,GLOBAL_CONTEXT
from langgraph_model.tools import (
    select_option,
    text_input,
    date_picker,
    number_input,
)

# ============================================================================
# LLM 模型
# ============================================================================

model = ChatOpenAI(
    model=MODEL_NAME,
    api_key=OPENAI_API_KEY,
    base_url=BASE_URL,
    temperature=0,
    max_tokens=4096,
)



# ============================================================================
# 工具定义（@tool 装饰器）
# ============================================================================

@tool
def go_to_step(runtime: ToolRuntime, step_name: str, reason: str = "") -> Command:
    """跳转到指定步骤（仅用户主动跳转时使用）"""
    target_step = STEP_NAMES.index(step_name) + 1
    dirty = get_dirty_range(target_step)
    display = STEP_DISPLAY_NAMES.get(step_name, step_name)
    updates: Dict[str, Any] = {
        "dirty_steps": set(runtime.state.get("dirty_steps", set()) or set()) | dirty,
        "last_updated": datetime.now().isoformat(),
    }
    msg = f"已跳转至 [{display}]。"
    if reason:
        msg += f" 原因：{reason}"
    msg += " 后续步骤已标记为待更新。"
    return Command(goto=step_name, update=updates, graph=Command.PARENT)


@tool
def proceed_to_next_step(
    runtime: ToolRuntime,
    step_answers: Dict[str, Any] = {},
    extra_data: Optional[Any] = None,
    qualification: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Command:
    """
    当前步骤完成，携带数据进入下一步。
    返回 Command 让 LangGraph 路由到下一个 step node。
    """
    messages = runtime.state.get("messages", [])
    last_ai_message = next(
        msg for msg in reversed(messages) if isinstance(msg, AIMessage)
    )
    current_step_name = None
    if hasattr(last_ai_message, 'name') and last_ai_message.name in STEP_NAMES:
        current_step_name = last_ai_message.name

    if not current_step_name:
        current_step_name = STEP_NAMES[0]

    # Map step name to step number: step2_initial=2, step3_common=3, etc.
    current_step_num = STEP_NAMES.index(current_step_name)
    target_step_num = current_step_num + 1
    next_step_name = STEP_NAMES[target_step_num]


    transfer_message = ToolMessage(
        content="跳转到下一步",
        tool_call_id=runtime.tool_call_id,
    )
    updates={
            "active_agent": next_step_name,
            "messages": [last_ai_message, transfer_message],
        }
    return Command(goto=next_step_name, update=updates, graph=Command.PARENT)


@tool
def request_missing_info(runtime: ToolRuntime, prompt: str) -> str:
    """追问用户缺失信息（不跳转步骤），返回追问内容"""
    return prompt


@tool
def back_to_previous_step(
    runtime: ToolRuntime,
    step_name: str,
    reason: str = "",
) -> Command:
    """返回指定步骤修改"""
    target_step_num = STEP_NAMES.index(step_name) + 1
    existing_dirty = set(runtime.state.get("dirty_steps", set()) or set()) | get_dirty_range(target_step_num)
    updates: Dict[str, Any] = {
        "current_step": target_step_num,
        "dirty_steps": existing_dirty,
        "last_updated": datetime.now().isoformat(),
    }
    # ToolMessage 由 agent 子图自动处理
    return Command(goto=step_name, update=updates, graph=Command.PARENT)


@tool
def finish_consultation(runtime: ToolRuntime) -> str:
    """用户确认咨询完成，结束流程"""
    return "感谢您使用宿迁市总工会劳动争议智能咨询系统，祝您维权顺利！"


@tool
def upload_evidence(
    runtime: ToolRuntime,
    file_content: str,
    filename: str,
    evidence_item_id: str,
) -> str:
    """上传证据文件并关联到证据项"""
    import uuid
    import base64
    import os

    file_id = f"file_{uuid.uuid4().hex[:12]}"
    session_id = runtime.state.get("session_id", "unknown")
    uploads_dir = f"data/uploads/{session_id}"
    os.makedirs(uploads_dir, exist_ok=True)

    try:
        decoded_content = base64.b64decode(file_content)
    except Exception:
        decoded_content = file_content.encode("utf-8")

    stored_path = f"{uploads_dir}/{file_id}_{filename}"
    with open(stored_path, "wb") as f:
        f.write(decoded_content)

    file_ref: FileRef = {
        "file_id": file_id,
        "filename": filename,
        "stored_path": stored_path,
        "uploaded_at": datetime.now().isoformat(),
        "evidence_item_id": evidence_item_id,
    }

    evidence_files = runtime.state.get("evidence_files") or {}
    evidence_files[file_id] = file_ref
    runtime.state["evidence_files"] = evidence_files

    evidence_items = runtime.state.get("evidence_items") or []
    for item in evidence_items:
        if item.get("id") == evidence_item_id:
            refs = item.get("uploaded_file_refs") or []
            refs.append(file_id)
            item["uploaded_file_refs"] = refs
            break
    runtime.state["evidence_items"] = evidence_items

    return (
        f"文件上传成功！\n"
        f"文件名：{filename}\n"
        f"文件ID：{file_id}\n"
        f"已关联证据项：{evidence_item_id}\n"
        f"可继续上传其他证据。"
    )


@tool
def request_lawyer_help(runtime: ToolRuntime) -> str:
    """打包案件数据，发送律师求助请求"""
    import uuid
    import json
    import os

    session_id = runtime.state.get("session_id", "unknown")
    request_id = f"lawyer_{uuid.uuid4().hex[:12]}"

    case_data = {
        "request_id": request_id,
        "session_id": session_id,
        "submitted_at": datetime.now().isoformat(),
        "case_category": runtime.state.get("case_category"),
        "qualification": runtime.state.get("qualification"),
        "step3_answers": runtime.state.get("step_data", {}).get("step3_common", {}).get("answers", {}),
        "step4_answers": runtime.state.get("step_data", {}).get("step4_special", {}).get("answers", {}),
        "evidence_items": runtime.state.get("evidence_items", []),
        "risk_assessment": runtime.state.get("risk_assessment"),
        "document_draft": runtime.state.get("document_draft"),
        "member_id": runtime.state.get("member_id"),
    }

    requests_dir = "data/lawyer_requests"
    os.makedirs(requests_dir, exist_ok=True)
    request_file = f"{requests_dir}/{request_id}.json"
    with open(request_file, "w", encoding="utf-8") as f:
        json.dump(case_data, f, ensure_ascii=False, indent=2)

    runtime.state["lawyer_help_status"] = "sent"

    return (
        f"律师求助请求已发送！\n"
        f"请求编号：{request_id}\n"
        f"值班律师将在1-3个工作日内回复。\n"
        f"回复将通过系统消息推送。"
    )



# ============================================================================
# 所有工具汇总（按 step 分组）
# ============================================================================

STEP_TOOL_SETS: Dict[str, List[Any]] = {
    "step2_initial": [
        proceed_to_next_step,
        go_to_step,
        request_missing_info,
        select_option,
        text_input,
        date_picker,
        number_input,
    ],
    "step3_common": [
        proceed_to_next_step,
        select_option,
        text_input,
        date_picker,
        number_input,
    ],
    "step4_special": [
        proceed_to_next_step,
    ],
    "step5_qualification": [
        proceed_to_next_step,
        request_missing_info,
    ],
    "step6_evidence": [
        proceed_to_next_step,
        upload_evidence,
        request_missing_info,
    ],
    "step7_risk": [
        proceed_to_next_step,
        request_missing_info,
    ],
    "step8_documents": [
        proceed_to_next_step,
        request_missing_info,
    ],
    "step9_roadmap": [
        proceed_to_next_step,
    ],
    "step10_review": [
        proceed_to_next_step,
        request_lawyer_help,
        request_missing_info,
        finish_consultation,
    ],
}


# ============================================================================
# 动态 Prompt 构建
# ============================================================================

def build_step_system_prompt(step_name: str, state: dict) -> str:
    """
    为指定步骤构建完整的 system prompt。
    = 全局上下文 + 步骤特有逻辑 + 当前案件状态
    """
    global_prompt = GLOBAL_CONTEXT
    step_prompt = STEP_PROMPTS.get(step_name, "")

    current_step = state.get("current_step", 1)
    case_category = state.get("case_category")
    session_id = state.get("session_id", "")
    dirty_steps = state.get("dirty_steps", set())
    completed_steps = state.get("completed_steps", set())

    current_step_num = STEP_NAMES.index(step_name) + 1 if step_name in STEP_NAMES else current_step
    is_dirty = current_step_num in dirty_steps and current_step_num in completed_steps

    context_lines = [
        "",
        "=" * 40,
        "【当前状态 - 请结合以下信息生成回复】",
        f"当前步骤：{current_step} ({STEP_DISPLAY_NAMES.get(step_name, step_name)})",
        f"会话ID：{session_id}",
        f"案由分类：{case_category or '尚未确定'}",
        f"已完成步骤：{sorted(completed_steps) if completed_steps else '无'}",
    ]

    step_data = state.get("step_data", {})

    if step_name == "step3_common" and "step2_initial" in step_data:
        step2_data = step_data.get("step2_initial", {}).get("answers", {})
        if step2_data:
            context_lines.append(f"\nStep2 用户选择：{step2_data}")

    if step_name == "step4_special":
        if "step3_common" in step_data:
            q_answers = step_data["step3_common"].get("answers", {})
            context_lines.append(f"\nStep3 通用问题回答：")
            for k, v in q_answers.items():
                context_lines.append(f"  {k}: {v}")
        if case_category:
            context_lines.append(f"\n主案由：{case_category}")

    if step_name == "step5_qualification":
        for sname in ["step3_common", "step4_special"]:
            if sname in step_data:
                answers = step_data[sname].get("answers", {})
                context_lines.append(f"\n{sname} 回答：")
                for k, v in answers.items():
                    context_lines.append(f"  {k}: {v}")

    if step_name == "step6_evidence":
        qual = state.get("qualification")
        if qual:
            context_lines.append(f"\n案件定性：")
            context_lines.append(f"  案由：{qual.get('case_types', [])}")
            rights = qual.get("rights_list", [])
            for r in rights:
                context_lines.append(f"  权益：{r.get('right_name')} = {r.get('amount')}元")

    if step_name == "step7_risk":
        evidence_items = state.get("evidence_items", [])
        if evidence_items:
            a_count = sum(1 for e in evidence_items if e.get("status") == "A")
            b_count = sum(1 for e in evidence_items if e.get("status") == "B")
            c_count = sum(1 for e in evidence_items if e.get("status") == "C")
            completeness = evaluate_evidence_completeness(evidence_items)
            context_lines.append(f"\n证据状态（已标记）：A={a_count}, B={b_count}, C={c_count}")
            context_lines.append(f"证据完整度：{completeness}")

    if step_name == "step8_documents":
        qual = state.get("qualification")
        if qual:
            context_lines.append(f"\n权益清单：")
            for r in qual.get("rights_list", []):
                context_lines.append(f"  {r.get('right_name')}: {r.get('amount')}元")
        evidence_items = state.get("evidence_items", [])
        if evidence_items:
            a_items = [e["name"] for e in evidence_items if e.get("status") == "A"]
            context_lines.append(f"\n已有证据（A类）：{a_items}")

    if step_name == "step9_roadmap":
        risk = state.get("risk_assessment")
        if risk:
            context_lines.append(f"\n风险等级：{risk.get('level', '未知')}")
            for rp in risk.get("risk_points", [])[:3]:
                if rp.get("is_high_risk"):
                    context_lines.append(f"  ⚠️ 高危：{rp.get('description', '')[:50]}")

    if step_name == "step10_review":
        qual = state.get("qualification")
        risk = state.get("risk_assessment")
        evidence_items = state.get("evidence_items", [])
        completeness = evaluate_evidence_completeness(evidence_items)
        context_lines.append(f"\n=== 案件摘要 ===")
        context_lines.append(f"案由：{qual.get('case_types', [case_category or '未确定'])[0] if qual else case_category or '未确定'}")
        if qual:
            rights = qual.get("rights_list", [])
            total = sum(r.get("amount", 0) or 0 for r in rights)
            context_lines.append(f"涉及金额：约{total:.0f}元")
        context_lines.append(f"证据完整度：{completeness}")
        if risk:
            context_lines.append(f"风险等级：{risk.get('level', '未知')}")

    context_lines.append("=" * 40)

    context_block = "\n".join(context_lines)

    return f"{global_prompt}\n{context_block}\n\n{step_prompt}"


# ============================================================================
# Step Agent 构建（使用 create_agent 子图 + name 参数）
# ============================================================================

# Agent 子图缓存（每个 step 一个实例）
_step_agents: Dict[str, Any] = {}


def _get_step_agent(step_name: str):
    """获取或创建指定步骤的 agent 子图（带 name 标识）"""
    if step_name in _step_agents:
        return _step_agents[step_name]

    tools = STEP_TOOL_SETS.get(step_name, [])

    # 使用全局上下文作为基础 system prompt
    # 动态部分会在 wrapper 中通过 messages 注入
    base_prompt = GLOBAL_CONTEXT + "\n\n" + STEP_PROMPTS.get(step_name, "")

    agent = create_agent(
        model,
        tools=tools,
        system_prompt=base_prompt,
        name=step_name,  # Agent 级别名称标识
    )
    _step_agents[step_name] = agent
    return agent


def _step_node_wrapper(step_name: str):
    """
    包装函数：调用 create_agent 子图。
    - 动态 system prompt 通过 messages 注入
    - 工具返回 Command(goto=..., graph=Command.PARENT) 由 LangGraph 自动处理路由
    """
    agent = _get_step_agent(step_name)

    def wrapper(state: ConsultationState) -> Command | Dict:
        # 构建动态 system prompt
        dynamic_prompt = build_step_system_prompt(step_name, state)

        # 将动态 prompt 注入到 messages 中
        messages = state.get("messages", [])

        # 如果第一条消息不是 SystemMessage，或者内容不同，则更新
        if not messages or not isinstance(messages[0], SystemMessage) or messages[0].content != dynamic_prompt:
            # 创建新的 messages 列表，第一条是动态 system prompt
            updated_messages = [SystemMessage(content=dynamic_prompt)]
            # 保留其他消息（跳过旧的 SystemMessage）
            for msg in messages:
                if not isinstance(msg, SystemMessage):
                    updated_messages.append(msg)

            # 更新状态
            state = {**state, "messages": updated_messages}

        response = agent.invoke(state)
        return response

    return wrapper


# ============================================================================
# StateGraph 构建
# ============================================================================

def _initialize_state(state: ConsultationState) -> Dict[str, Any]:
    """
    初始化状态节点：确保所有必需字段都有默认值。
    只在首次调用时初始化，后续调用保持现有值。
    """
    updates = {}

    # 初始化 current_step（如果未设置或为 0）
    # step2_initial is step 2, so default to 2
    if state.get("current_step") is None or state.get("current_step") == 0:
        updates["current_step"] = 2

    # 初始化其他必需字段
    if state.get("completed_steps") is None:
        updates["completed_steps"] = set()

    if state.get("step_data") is None:
        updates["step_data"] = {}

    if state.get("dirty_steps") is None:
        updates["dirty_steps"] = set()

    if state.get("evidence_items") is None:
        updates["evidence_items"] = []

    if state.get("evidence_files") is None:
        updates["evidence_files"] = {}

    return updates


def _route_from_start(state: ConsultationState) -> str:
    """
    入口路由：根据 current_step 恢复到对应步骤节点。
    每次新的 invoke 从 START 进入，由这里路由到正确的步骤。

    Mapping: current_step matches the step number in the name
    - current_step=2 → step2_initial
    - current_step=3 → step3_common
    - etc.
    """
    current = state.get("current_step", 2)
    if current is None or current == 0:
        current = 2

    # 确保 current 是整数类型
    try:
        current = int(current)
    except (ValueError, TypeError):
        current = 2

    # Map current_step to STEP_NAMES index: step2_initial is at index 0, so offset by 2
    if 2 <= current <= len(STEP_NAMES) + 1:
        return STEP_NAMES[current - 2]
    return STEP_NAMES[0]  # 默认从 step2_initial 开始


def _route_after_step(state: ConsultationState) -> str:
    """
    交互模式路由：每次 step node 执行后检查是否结束本轮对话。
    
    - 如果 LLM 返回了普通 AIMessage（无导航工具调用）→ 返回 END，等待用户下一条消息
    - 如果 LLM 调用了导航工具（如 proceed_to_next_step）→ 工具返回 Command(goto=next_step)
      绕过了条件边，graph 直接跳转到目标节点
    """
    messages = state.get("messages", [])
    if messages:
        last = messages[-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            # LLM 调用了工具，导航工具会在 Command 中指定目标
            # 条件边这里返回什么无所谓，Command(goto=...) 会覆盖
            return END
        if hasattr(last, "type") and last.type == "ai":
            # LLM 直接回复（无工具调用）→ 暂停等待用户输入
            return END
    active = state.get("active_agent")
    return active if active else END


def create_consultation_graph():
    """
    构建九步咨询系统 StateGraph。

    架构（Agentic Handoffs 模式）：
    - 每个步骤是一个 create_agent 子图，带 name 参数标识
    - 导航工具返回 Command(goto=..., graph=Command.PARENT) 控制父图路由
    - 条件边检测最后消息：普通 AIMessage → END（等待用户）
    - 用户输入后重新从 START 进入，走到对应步骤节点继续
    """
    workflow = StateGraph(
        ConsultationState,
        input_schema=ConsultationInput,
    )

    # 添加状态初始化节点
    workflow.add_node("_init", _initialize_state)

    # 添加所有步骤节点（使用 create_agent 子图）
    for step_name in STEP_NAMES:
        workflow.add_node(step_name, _step_node_wrapper(step_name))

    # 起点 → 初始化节点
    workflow.add_edge(START, "_init")

    # 初始化节点 → 当前步骤（根据 current_step 恢复检查点）
    workflow.add_conditional_edges(
        "_init",
        _route_from_start,
        {name: name for name in STEP_NAMES},
    )

    # 每个步骤后加条件边：无导航工具调用时暂停，等待用户输入
    for step_name in STEP_NAMES:
        workflow.add_conditional_edges(
            step_name,
            _route_after_step,
            STEP_NAMES + [END],
        )

    checkpointer = InMemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# ============================================================================
# 单例
# ============================================================================

_graph_instance: Optional[Any] = None


def get_consultation_graph() -> Any:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = create_consultation_graph()
    return _graph_instance


