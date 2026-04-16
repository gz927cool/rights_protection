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

## 当前状态（从上下文获取）

系统已提供案由分类信息：
- 如果"案由分类"显示为"尚未确定"，说明需要提取案由
- 如果"案由分类"已显示具体类型（如"欠薪"），说明案由已提取，直接进入第二步

## 执行顺序（严格按顺序，禁止跳步）

### 第一步：提取案由

**如果"案由分类"已确定为某类型**（如"欠薪"）：
1. case_category_extracted = true（无需再提取）
2. 直接输出确认："好的，您的案件属于【{已确定类型}】类争议。"
3. 进入第二步

**如果"案由分类"为"尚未确定"**：
如果用户输入中包含案由关键词（欠薪/克扣/开除/工伤/调岗/社保），则：
1. 立即提取 case_category（见下方映射）
2. 确认案由：直接输出"好的，您的案件属于【欠薪】类争议。"
3. case_category_extracted = true
4. 进入第二步

如果用户没有提供案由关键词：
1. 输出"请问您遇到了什么类型的劳动争议？[欠薪/开除/工伤/调岗/社保/其他]"
2. 等待用户回复
3. 用户回复后提取 case_category，case_category_extracted = true
4. 进入第二步

案由映射：
- 欠薪/克扣工资/拖欠工资/加班费 → case_category = "欠薪"
- 开除/辞退/解除合同/被公司赶走 → case_category = "开除"
- 工伤/工作受伤/职业伤害 → case_category = "工伤"
- 调岗/降薪/岗位调整 → case_category = "调岗"
- 社保/保险/公积金 → case_category = "社保"
- 其他/其他争议 → case_category = "其他"
- 数字 1-6 → 按顺序对应上述

### 第二步：提取路径

**重要：只有当 case_category_extracted = true 时才能进入第二步**

**检查用户输入是否包含路由选择**：
- 如果用户输入包含"A"、"律师"、"视频" → route = "video_call"
- 如果用户输入包含"B"、"自由描述"、"我描述"、"我说" → route = "free_description"
- 如果用户输入包含"C"、"交互"、"问答"、"清单"、"系统" → route = "interactive_qa"

**如果提取到了 route（用户输入包含路由关键词）**：
1. 直接输出"好的，您选择了[B)自由描述案情]。正在进入下一步..."
2. 设置 route_extracted = true
3. **立即执行第三步（调用 proceed_to_next_step）**

**如果用户输入不包含路由关键词**：
→ 输出"请选择处理方式：A)转律师视频 B)自由描述案情 C)交互式问答"

设置 route_extracted = true

### 第三步：结束（必须立即执行）

**重要：只有当 route_extracted = true 时才能执行此步**

调用 proceed_to_next_step，携带：
step_answers={"case_category": "[已提取的案由]", "route": "[已提取的路径]"}

## 禁止事项（违反则对话顺序混乱）
- 如果"案由分类"显示"尚未确定"，必须先提取案由，不能直接展示A/B/C选项
- case_category_extracted=false 时，禁止展示 A/B/C 路径选项
- route_extracted=true 后，禁止再询问案由或展示案由选项
- proceed_to_next_step 必须携带 step_answers 参数，其中包含 case_category 和 route
""",

    "step3_common": """## 本步任务：12个通用问题收集

按顺序逐题收集12个通用问题。每次只问一个问题。

## 状态跟踪（重要）

在思考时，必须维护以下状态变量：
- current_question: 当前要问的问题编号（初始=1）
- answers: 已收集的回答字典（初始={}）

**从对话历史中提取已收集的回答**：
- 仔细阅读之前所有用户消息，提取已回答的问题和答案
- 如果用户回答了Q1，就把"就业状态"和答案加入answers字典

## 问题列表

Q1. 就业状态 → key="就业状态", 选项：在职/离职/待岗
Q2. 离职时间 → key="离职时间", 仅当Q1选择"离职"或"待岗"时询问
Q3. 签订劳动合同 → key="签订劳动合同", 选项：是/否/不确定
Q4. 月工资 → key="月工资", 格式：数字
Q5. 工资发放方式 → key="工资发放方式", 选项：银行转账/现金/微信/支付宝
Q6. 社保缴纳 → key="社保缴纳", 选项：全部/未缴/部分
Q7. 工作岗位 → key="工作岗位", 示例：职员/工人/外卖员等
Q8. 入职时间 → key="入职时间", 格式：日期
Q9. 每周工作时间 → key="每周工作时间", 选项：标准工时/综合工时/加班
Q10. 涉及诉求 → key="涉及诉求", 选项：欠薪/赔偿金/社保等
Q11. 涉及金额 → key="涉及金额", 格式：数字（元）
Q12. 期望结果 → key="期望结果", 选项：继续上班/拿钱走人/补缴社保

## 交互规则
- **根据current_question确定要问的问题**
- 如果current_question=1，先问Q1就业状态
- 用户回答后，更新answers字典，current_question加1
- 继续问下一个问题，直到Q12完成
- 如果用户输入"跳过"或"跳过剩余问题"，立即调用proceed_to_next_step

## 条件问题逻辑
- Q2（离职时间）：只有当answers["就业状态"]是"离职"或"待岗"时才询问
- 其他问题按顺序询问

## 结束条件
- Q12完成或用户要求跳过 → 调用 proceed_to_next_step
- 携带参数：step_answers=answers（所有收集到的回答）
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

基于 step3 和 step4 的回答，结合三级案由体系，生成规范化的案件描述和权益清单。

## 第一步：读取案件事实

从 step3_common 和 step4_special 的 answers 中提取：
- 用人单位名称
- 入职时间、离职时间（如有）
- 月工资、工资发放方式
- 劳动关系状态
- 诉求类型（欠薪/开除/工伤/调岗/社保）
- 涉及金额
- 特殊事实（如加班、合同签订情况等）

## 第二步：匹配三级案由（重要）

根据案件事实，从以下案由体系中匹配最合适的三级案由。

### 欠薪类（初始案由=欠薪）优先匹配：
- 追索基本工资纠纷 > 工资扣减与拖欠支付纠纷
  关键词：克扣工资、拖欠工资、停工停产
- 追索加班工资纠纷 > 加班事实认定纠纷
  关键词：加班、延长工时、值班
- 追索加班工资纠纷 > 特殊情形下的加班费争议
  关键词：包薪制、年薪制、综合工时
- 奖金/提成/绩效工资纠纷 > 支付条件成就争议
  关键词：提成、绩效、奖金、佣金
- 津贴/补贴发放纠纷
  关键词：高温津贴、夜班津贴、岗位津贴

### 开除类（初始案由=开除）优先匹配：
- 违法解除/终止劳动合同赔偿金纠纷 > 解除事实依据不足争议纠纷
  关键词：被辞退、被开除、违法解除
- 违法解除/终止劳动合同赔偿金纠纷 > 解除理由与事实不符争议纠纷
  关键词：旷工认定、违纪事实不符
- 用人单位单方解除劳动合同纠纷 > 因劳动者严重违纪解除纠纷
  关键词：违反规章制度、严重违纪
- 协商解除劳动合同纠纷 > 就经济补偿/赔偿金支付产生的纠纷
  关键词：协商解除、补偿金额
- 劳动者单方解除劳动合同纠纷 > 劳动者即时解除（被迫离职）纠纷
  关键词：被迫离职、未缴社保、未发工资

### 工伤类（初始案由=工伤）优先匹配：
- 工伤保险待遇纠纷 > 停工留薪期工资（原工资福利待遇）争议纠纷
- 工伤保险待遇纠纷 > 一次性伤残待遇争议纠纷
- 工伤保险待遇纠纷 > 工伤医疗费及康复费争议纠纷

### 调岗类（初始案由=调岗）优先匹配：
- 履行/变更劳动合同纠纷 > 单方调岗合理性认定纠纷
  关键词：强制调岗、降薪调岗、不胜任调岗
- 履行/变更劳动合同纠纷 > 薪酬调整（降薪）合法性纠纷
  关键词：降薪、工资减少

## 第三步：生成案件事实描述

格式：
"申请人[姓名]于[入职时间]入职[用人单位]，担任[岗位]，
[劳动关系状态：全职/非全日制]。因[核心争议内容]，
产生劳动争议。涉及金额约[金额]元。"

## 第四步：生成权益清单

根据案由和事实，对应生成权益项，每项包含：
- right_name: 权益名称
- amount: 金额（计算得出）
- calculation_basis: 计算依据（如：2个月 × 12,000元/月）
- legal_basis: 法律依据（如：《劳动合同法》第30条）

### 常见权益计算公式（根据案由套用）
- 欠薪：月数 × 月工资
- 违法解除(2N)：年限 × 2 × 月工资（最高12年）
- 经济补偿金(N)：年限 × 月工资（满6个月按1年算，不满6个月按0.5年算）
- 未签合同双倍工资差额：11个月 × 月工资（入职第2个月起算，最多11个月）
- 加班费：延长工时×1.5倍/休息日×2倍/法定节假日×3倍 × 小时工资
- 未休年休假工资：未休假天数 × 日工资 × 3倍（其中2倍为工资，1倍为补偿）

## 输出格式（严格按此格式输出）

```
【案件事实】
[规范化描述]

【案由定性】
一级案由：[匹配的一级案由]
二级案由：[匹配的二级案由]
三级案由：[匹配的三级案由]
三级案由说明：[三级案由的纠纷描述]

【权益清单】
| 序号 | 权益名称 | 金额 | 计算依据 | 法律依据 |
|------|----------|------|----------|----------|
| 1 | [名称] | [金额]元 | [计算过程] | [法条] |
...

请确认以上内容是否准确，如有误请指出。
```

## 结束条件
用户确认"准确"或"继续"后，调用 proceed_to_next_step，携带：
{"qualification": {"case_facts": "...", "case_types": ["一级/二级/三级"], "rights_list": [...], "legal_basis": [...]}}
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
# 交互类工具（generate-ui 组件生成）
# ============================================================================

@tool
def select_option(runtime: ToolRuntime, options: List[str], question: str) -> str:
    """
    请求用户从选项列表中选择。
    - options: 可选列表，如 ["劳动合同", "劳务合同", "实习合同"]
    - question: 向用户展示的问题文字
    返回格式化的选择提示，供前端渲染为选择按钮组件。
    """
    import json as _json
    payload = _json.dumps({
        "component": "select_option",
        "question": question,
        "options": options,
    })
    return f"[SELECT_OPTION]{payload}[/SELECT_OPTION]"


@tool
def text_input(
    runtime: ToolRuntime,
    question: str,
    placeholder: str = "",
    multiline: bool = False,
) -> str:
    """
    请求用户输入文本。
    - question: 向用户展示的问题文字
    - placeholder: 输入框占位提示
    - multiline: 是否允许多行输入
    返回格式化的文本输入提示，供前端渲染为文本输入组件。
    """
    import json as _json
    payload = _json.dumps({
        "component": "text_input",
        "question": question,
        "placeholder": placeholder,
        "multiline": multiline,
    })
    return f"[TEXT_INPUT]{payload}[/TEXT_INPUT]"


@tool
def date_picker(runtime: ToolRuntime, question: str) -> str:
    """
    请求用户选择日期。
    - question: 向用户展示的问题文字
    返回格式化的日期选择提示，供前端渲染为日期选择器组件。
    """
    import json as _json
    payload = _json.dumps({
        "component": "date_picker",
        "question": question,
    })
    return f"[DATE_PICKER]{payload}[/DATE_PICKER]"


@tool
def number_input(
    runtime: ToolRuntime,
    question: str,
    min_value: float = 0,
    max_value: float = 999999999,
    unit: str = "",
) -> str:
    """
    请求用户输入数字。
    - question: 向用户展示的问题文字
    - min_value: 最小值
    - max_value: 最大值
    - unit: 单位，如 "元"、"天" 等
    返回格式化的数字输入提示，供前端渲染为数字输入组件。
    """
    import json as _json
    payload = _json.dumps({
        "component": "number_input",
        "question": question,
        "min": min_value,
        "max": max_value,
        "unit": unit,
    })
    return f"[NUMBER_INPUT]{payload}[/NUMBER_INPUT]"


# ============================================================================
# 所有工具汇总（按 step 分组）
# ============================================================================

STEP_TOOL_SETS: Dict[str, List[Any]] = {
    "step2_initial": [
        proceed_to_next_step,
        go_to_step,
        request_missing_info,
        back_to_previous_step,
        select_option,
        text_input,
        date_picker,
        number_input,
    ],
    "step3_common": [
        proceed_to_next_step,
        request_missing_info,
        back_to_previous_step,
        select_option,
        text_input,
        date_picker,
        number_input,
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

                # Lightweight wrapper so tools can read/write state via runtime.state
                class _Runtime:
                    def __init__(self, st):
                        self.state = st
                result = matched.func(runtime=_Runtime(state), **tool_args)

                if isinstance(result, Command):
                    goto = result.goto if hasattr(result, "goto") else END
                    update = result.update if hasattr(result, "update") else {}

                    tool_msg = ToolMessage(
                        content=str(result) if result else "",
                        tool_call_id=call.get("id", ""),
                    )
                    all_messages.append(tool_msg)

                    final_dict: Dict[str, Any] = {
                        "messages": all_messages,
                        "tool_results": [{
                            "id": call.get("id", ""),
                            "name": tool_name,
                            "result": str(result) if result else "",
                        }],
                    }
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


