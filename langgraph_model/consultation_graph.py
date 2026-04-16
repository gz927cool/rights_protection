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

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langgraph.errors import ParentCommand
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain.tools import tool, ToolRuntime

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
# 全局上下文：所有 Agent 共享
# ============================================================================

GLOBAL_CONTEXT = """## 系统信息
你是宿迁市总工会劳动争议智能咨询系统的AI法律助手。
当前版本：九步引导式咨询系统 v2.0

## 全局流程说明
用户正在经历一个结构化的九步咨询流程：
1. 模式选择 - 选择律师视频或AI智能问答
2. 问题初判 - 确定咨询路径
3. 通用问题 - 12个基础问题
4. 特殊问题 - 按案由追问
5. 案件定性 - 生成权益清单
6. 证据攻略 - 收集证据
7. 风险提示 - 风险评估
8. 文书生成 - 生成仲裁申请
9. 行动路线图 - 维权指引
10. 求助复核 - AI复核+律师求助

## 你的角色定位
- 你是一个专业、温暖的法律咨询助手
- 始终用中文回复
- 用通俗易懂的语言解释法律术语
- 注意识别用户情感状态，适当安抚

## 工具调用原则（重要 - 必须遵守）
当你需要执行一个动作（如跳转到下一步、返回上一步、暂停保存等）时，
你必须调用对应的工具。直接回复用户的文本问题，不需要调用任何工具。

### 可用命令工具
- proceed_to_next_step: 结束当前步骤，进入下一步（必须携带必要的参数）
- back_to_previous_step: 返回上一步修改
- go_to_step: 跳转到指定步骤
- request_missing_info: 追问用户缺失信息
- pause_and_save: 暂停并保存进度
- finish_consultation: 完成咨询
- upload_evidence: 上传证据文件
- request_lawyer_help: 一键求助律师

## 状态字段说明
当前案件状态（从 state 中注入）：
- current_step: 当前步骤编号 (1-10)
- case_category: 案由分类（欠薪/开除/工伤/调岗/社保/其他）
- session_id: 会话ID

## 脏数据处理
如果 dirty_steps 包含当前步骤，说明之前的回答已被修改。
你应该告知用户："检测到之前的回答已被修改，当前内容已标记为待更新。"

## 严格遵守
- 回复应当帮助用户完成当前步骤的任务
- 调用工具后等待结果，根据结果继续对话
"""

# ============================================================================
# 步骤特有 Prompt（每步独立）
# ============================================================================

STEP_PROMPTS: Dict[str, str] = {


    "step2_initial": """## 本步任务：问题初判

用户已选择【AI智能问答】。现在需要确定处理路径。

## 三条处理路径

### 路径A：转律师视频
触发条件：用户情况紧急/涉及重大金额/明确要求律师介入

### 路径B：自由描述案情
触发条件：用户开始描述具体问题/表达了明确的争议内容
处理方式：认真倾听，提取关键信息，识别情感状态，展示6大案由图标确认

### 路径C：交互式问答
触发条件：用户希望系统化梳理/没有明确案情描述

## 案由分类（6类）
- 欠薪：工资、加班费、绩效奖金被扣/拖欠
- 开除：被辞退、解除劳动合同、赔偿金争议
- 工伤：工作受伤、工伤认定、工伤赔偿
- 调岗：岗位调整、降薪、工作内容变更
- 社保：社保欠缴、未缴、断缴
- 其他：上述以外的其他劳动争议

## 结束条件
调用 proceed_to_next_step，携带：
- route: "video_call" / "free_description" / "interactive_qa"
- case_category: 用户选择的案由（如果有）
""",

    "step3_common": """## 本步任务：12个通用问题收集

按顺序逐题收集12个通用问题。每次只问一个问题。

## 问题列表

Q1. 就业状态 → radio: 在职/离职/待岗
Q2. 离职时间 → calendar（仅Q1选离职/待岗时显示）
Q3. 签订劳动合同 → radio: 是/否/不确定
Q4. 月工资 → number（元/月）
Q5. 工资发放方式 → radio: 银行转账/现金/微信/支付宝
Q6. 社保缴纳 → radio: 全部/未缴/部分
Q7. 工作岗位 → dropdown（工厂工人/外卖员/职员等）
Q8. 入职时间 → calendar
Q9. 每周工作时间 → radio: 标准工时/综合工时/加班
Q10. 涉及诉求 → checkbox（欠薪/赔偿金/社保等）
Q11. 涉及金额 → number（元）
Q12. 期望结果 → radio: 继续上班/拿钱走人/补缴社保

## 交互规则
- 每次只问一题
- 根据题型展示对应控件
- 前序答案影响后续问题显示
- Q10完成后判断主案由

## 结束条件
Q1-Q12全部完成或用户主动跳过剩余问题
调用 proceed_to_next_step，携带 Q1-Q12 全部回答
""",

    "step4_special": """## 本步任务：案由特殊问题追问

基于 step3 的案由判断，从特殊问题库加载追问。

## 核心事实清单（STOP_FACTS）
每回答一题后判断是否已厘清：
1. 用人单位名称
2. 入职时间
3. 劳动关系状态
4. 核心争议内容
5. 涉及金额

## 案由特殊问题（欠薪/开除/工伤/调岗/社保各有一套）

## 结束条件
5个核心事实全部厘清 → proceed_to_next_step
用户主动要求跳过 → proceed_to_next_step
""",

    "step5_qualification": """## 本步任务：案件定性 + 权益清单生成

基于 step3 和 step4 的回答，生成规范化的案件描述和权益清单。

## 输出要求

### 1. 案件事实描述
生成一段规范化的案件描述：当事人信息、劳动关系基本情况、核心争议经过、金额计算

### 2. 案由编码（三级）
一级：劳动争议；二级：劳动合同纠纷/工伤保险待遇纠纷/社会保险纠纷；三级：根据核心诉求确定

### 3. 权益清单
为每个权益项生成：right_name, amount, calculation_basis, legal_basis

### 常见权益计算
- 欠薪：月数 × 月工资
- 违法解除(2N)：年限 × 2 × 月工资（最高12年）
- 经济补偿金(N)：年限 × 月工资
- 未签合同双倍工资：11个月 × 月工资

## 用户确认
展示完毕后询问："以上内容是否准确？如有误请指出。"

## 结束条件
用户确认后调用 proceed_to_next_step，携带 qualification（含案件事实、案由编码、权益清单、法律依据）
""",

    "step6_evidence": """## 本步任务：证据攻略

基于 case_category 从证据库加载对应证据清单。

## 证据状态标记
引导用户为每项标记：
- A（已有）：已持有，准备上传
- B（可补充）：可以通过努力获取
- C（无法获得）：客观上无法获取

## 证据完整度评级
- 充分：A类证据≥3个，A+B≥80%
- 基本完整：A类≥2个，或A+B≥60%
- 不完整：A类=1个，或A+B<60%
- 严重缺乏：A类=0

## 结束条件
调用 proceed_to_next_step，携带 evidence_items（含状态标记）和 evidence_completeness（评级）
""",

    "step7_risk": """## 本步任务：风险评估

综合分析案件事实、证据完整度，给出风险提示。

## 风险等级
- 高危：时效过期/关键证据全缺/充分抗辩理由
- 中危：部分证据缺失/计算可能偏差
- 低危：证据充分/事实清楚

## 结束条件
调用 proceed_to_next_step，携带 risk_assessment
""",

    "step8_documents": """## 本步任务：文书生成

基于案件信息、证据清单、权益清单，生成仲裁申请书。

## 文书修改
用户可以提问：
- "这个金额怎么计算？" → 解释计算逻辑
- "能帮我修改表述吗？" → 提供修改建议

## 结束条件
调用 proceed_to_next_step，携带 document_draft
""",

    "step9_roadmap": """## 本步任务：行动路线图

展示三步维权路径：协商 → 调解 → 仲裁

## 宿迁市总工会调解热线
0527-843XXXXX（适宜调解案件优先推荐）

## 结束条件
调用 proceed_to_next_step，进入 step10_review
""",

    "step10_review": """## 本步任务：求助复核

提供预设复核模板和一键律师求助。

## 预设复核模板（10个）
1. 证据检查：证据清单是否充分？
2. 金额计算：赔偿金额计算对吗？
3. 胜算评估：仲裁胜算多大？
4. 策略咨询：先协商还是直接仲裁？
5. 文书检查：申请书有没有问题？
6. 证据获取：B类证据怎么获取？
7. 信息纠错：发现之前回答错了
8. 法律解读：涉及哪些法律条款？
9. 时间规划：维权时间线是什么？
10. 备选方案：仲裁不受理怎么办？

## 一键求助律师
发送完整案件材料给工会值班律师，值班律师将在1-3个工作日内回复。

## 结束条件
用户点击"完成咨询" → finish_consultation
用户选择继续 → proceed_to_next_step（进入路线图）
""",
}


# ============================================================================
# Mock Runtime（工具函数内访问 state）
# ============================================================================

class MockRuntime:
    """模拟 ToolRuntime，让工具函数可以读写 state"""
    def __init__(self, state: Dict):
        self.state = state


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
    return Command(goto=step_name, update=updates)


@tool
def proceed_to_next_step(
    runtime: ToolRuntime,
    step_answers: Dict[str, Any],
    extra_data: Optional[Any] = None,
) -> Command:
    """
    当前步骤完成，携带数据进入下一步。
    返回 Command 让 LangGraph 路由到下一个 step node。
    """
    import json as _json

    current_step_num = runtime.state.get("current_step", 1)
    current_step_name = STEP_NAMES[current_step_num - 1]
    target_step_num = current_step_num + 1

    extra = {}
    if extra_data:
        if isinstance(extra_data, str):
            try:
                extra = _json.loads(extra_data)
            except Exception:
                extra = {"raw": extra_data}
        elif isinstance(extra_data, dict):
            extra = extra_data

    step_data = (runtime.state.get("step_data", {}) or {}).copy()
    step_data[current_step_name] = StepData(
        answers=step_answers,
        status="completed",
        completed_at=datetime.now().isoformat(),
        extra=extra,
    )

    updates: Dict[str, Any] = {
        "step_data": step_data,
        "current_step": target_step_num,
        "completed_steps": set(runtime.state.get("completed_steps", set()) or set()) | {current_step_num},
        "dirty_steps": set(runtime.state.get("dirty_steps", set()) or set()) | get_dirty_range(target_step_num),
        "last_updated": datetime.now().isoformat(),
    }

    if current_step_name == "step2_initial":
        case_category = step_answers.get("case_category")
        if case_category:
            updates["case_category"] = case_category
        route = step_answers.get("route")
        if route == "video_call":
            updates["case_category"] = "__VIDEO_CALL__"

    if current_step_name == "step3_common":
        case_category = step_answers.get("case_category")
        if case_category:
            updates["case_category"] = case_category

    # 路由目标：下一个 step node 的名字
    if target_step_num > len(STEP_NAMES):
        return Command(goto=END, update=updates)
    next_step_name = STEP_NAMES[target_step_num - 1]
    return Command(goto=next_step_name, update=updates)


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
    return Command(goto=step_name, update=updates)


@tool
def pause_and_save(runtime: ToolRuntime) -> str:
    """暂停并保存进度"""
    token = (runtime.state.get("session_id", "") or "") + "_paused"
    return (
        f"进度已保存。您的恢复码：[{token}]。"
        f"下次输入此码即可继续。"
    )


@tool
def check_and_apply_dirty(
    runtime: ToolRuntime,
    action: Literal["recalculate", "keep"],
) -> str:
    """脏数据确认：重新计算或保留现有内容"""
    if action == "recalculate":
        return "脏数据已清除，将重新生成。"
    return "现有内容已保留，继续。"


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
        back_to_previous_step,
    ],
    "step3_common": [
        proceed_to_next_step,
        request_missing_info,
        back_to_previous_step,
    ],
    "step4_special": [
        proceed_to_next_step,
        request_missing_info,
        back_to_previous_step,
    ],
    "step5_qualification": [
        proceed_to_next_step,
        request_missing_info,
        back_to_previous_step,
    ],
    "step6_evidence": [
        proceed_to_next_step,
        upload_evidence,
        request_missing_info,
        back_to_previous_step,
    ],
    "step7_risk": [
        proceed_to_next_step,
        request_missing_info,
        back_to_previous_step,
    ],
    "step8_documents": [
        proceed_to_next_step,
        request_missing_info,
        back_to_previous_step,
    ],
    "step9_roadmap": [
        proceed_to_next_step,
        back_to_previous_step,
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

    if is_dirty:
        context_lines.append("⚠️ 注意：检测到之前的回答已被修改，当前内容可能需要更新！")

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
# Step Node 构建（使用 @tool + bind_tools）
# ============================================================================

def _build_step_node(step_name: str):
    """
    为指定步骤构建一个 node 函数。
    使用 @tool 装饰的工具 + model.bind_tools() 循环处理。
    """
    tools = STEP_TOOL_SETS.get(step_name, STEP_TOOL_SETS["step2_initial"])
    tools_by_name = {t.name: t for t in tools}
    bound_model = model.bind_tools(tools)

    def node(state: ConsultationState) -> Dict:
        # 交互模式：检查是否从 interrupt 恢复（用户已输入新消息）
        resume_input = state.get("__resume_input__")
        if resume_input:
            # 从 interrupt 恢复：用户输入了消息，追加到消息列表
            state["messages"].append(HumanMessage(content=resume_input, type="human"))
            state.pop("__resume_input__", None)

        # 1. 自动加载证据清单（step6 首次进入时）
        return_dict: Dict[str, Any] = {}
        if step_name == "step6_evidence" and not state.get("evidence_items"):
            case_category = state.get("case_category")
            if case_category and case_category not in ("__VIDEO_CALL__",):
                items = get_evidence_checklist(case_category)
                if items:
                    return_dict["evidence_items"] = items

        # 2. 动态构建 system prompt
        system_prompt = build_step_system_prompt(step_name, state)

        # 3. 构造消息历史：SystemMessage(prompt) + 用户消息（截断旧消息防止超出token限制）
        MAX_CONTEXT_MESSAGES = 10  # 保留最近N条消息，节省token
        raw_messages = list(state.get("messages", []))
        trimmed_messages = raw_messages[-MAX_CONTEXT_MESSAGES:] if len(raw_messages) > MAX_CONTEXT_MESSAGES else raw_messages
        all_messages: List[Any] = [SystemMessage(content=system_prompt)] + list(trimmed_messages)

        # 4. 单次 LLM 调用
        ai_msg = bound_model.invoke(all_messages)
        all_messages.append(ai_msg)

        tool_calls = ai_msg.tool_calls if hasattr(ai_msg, 'tool_calls') else []

        # 5. 导航工具调用 → 直接跳转，不 interrupt
        if tool_calls:
            for call in tool_calls:
                tool_name = call.get("name", "")
                tool_args = call.get("args", {})
                matched = tools_by_name.get(tool_name)
                if not matched:
                    continue

                mock_runtime = MockRuntime(state)
                result = matched.func(runtime=mock_runtime, **tool_args)

                if isinstance(result, Command):
                    goto = result.goto if hasattr(result, "goto") else END
                    update = result.update if hasattr(result, "update") else {}

                    tool_msg = ToolMessage(
                        content=str(result) if result else "",
                        tool_call_id=call.get("id", ""),
                    )
                    all_messages.append(tool_msg)

                    final_dict: Dict[str, Any] = {"messages": all_messages}
                    final_dict.update(update)
                    if return_dict.get("evidence_items") and "evidence_items" not in final_dict:
                        final_dict["evidence_items"] = return_dict["evidence_items"]

                    return Command(goto=goto, update=final_dict)
                else:
                    tool_msg = ToolMessage(
                        content=str(result),
                        tool_call_id=call.get("id", ""),
                    )
                    all_messages.append(tool_msg)

        # 6. 无导航工具调用 → 返回普通字典，让条件边决定路由
        final_dict: Dict[str, Any] = {"messages": all_messages}
        final_dict.update(return_dict)
        return final_dict

    return node


# ============================================================================
# 证据初始化 Node（step6 专用）
# ============================================================================

def _build_evidence_init_node():
    """step6 进入时，从 case_category 加载证据清单到 state"""
    def node(state: ConsultationState) -> Dict:
        case_category = state.get("case_category")
        if case_category and case_category not in ("__VIDEO_CALL__",):
            items = get_evidence_checklist(case_category)
            return {"evidence_items": items}
        return {}
    return node


# ============================================================================
# 证据完整度评估 Node（step6 离开时）
# ============================================================================

def _build_evidence_completeness_node():
    """评估证据完整度并写入 step_data"""
    def node(state: ConsultationState) -> Dict:
        evidence_items = state.get("evidence_items", [])
        if not evidence_items:
            return {}

        completeness = evaluate_evidence_completeness(evidence_items)
        step_data = (state.get("step_data", {}) or {}).copy()
        if "step6_evidence" not in step_data:
            step_data["step6_evidence"] = StepData(
                answers={},
                status="in_progress",
                completed_at=None,
                extra={"evidence_completeness": completeness},
            )
        else:
            step_data["step6_evidence"]["extra"]["evidence_completeness"] = completeness

        return {"step_data": step_data}
    return node


# ============================================================================
# 路由函数
# ============================================================================
# ============================================================================
# StateGraph 构建
# ============================================================================

def _route_from_start(state: ConsultationState) -> str:
    """
    入口路由：根据 current_step 恢复到对应步骤节点。
    每次新的 invoke 从 START 进入，由这里路由到正确的步骤。
    """
    current = state.get("current_step", 1)
    msg_count = len(state.get("messages", []))
    if 1 <= current <= len(STEP_NAMES):
        return STEP_NAMES[current - 1]
    return STEP_NAMES[0]  # 默认从 step1 开始


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
    return END


def create_consultation_graph():
    """
    构建九步咨询系统 StateGraph。

    架构（Phase 5 重构 - Handoffs 模式）：
    - 每步 node 用 @tool + model.bind_tools() 处理工具调用
    - 节点返回普通 dict（LLM 无导航工具）或 Command(goto=next_step)（导航工具）
    - 条件边检测最后消息：普通 AIMessage → END（等待用户）；导航工具由 Command 处理
    - 用户输入后重新从 START 进入，走到对应步骤节点继续
    """
    workflow = StateGraph(
        ConsultationState,
        input_schema=ConsultationInput,
    )

    # 添加所有步骤节点
    for step_name in STEP_NAMES:
        workflow.add_node(step_name, _build_step_node(step_name))

    # 起点 → 当前步骤（根据 current_step 恢复检查点）
    workflow.add_conditional_edges(
        START,
        _route_from_start,
        {name: name for name in STEP_NAMES},
    )

    # 每个步骤后加条件边：LLM 无导航工具调用时暂停，等待用户输入
    for step_name in STEP_NAMES:
        workflow.add_conditional_edges(
            step_name,
            _route_after_step,
            {END: END},
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


# ============================================================================
# 便利入口
# ============================================================================

def start_consultation(
    session_id: str,
    member_id: Optional[str] = None,
    resume_token: Optional[str] = None,
) -> Dict:
    return create_initial_state(session_id, member_id)
