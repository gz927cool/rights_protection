"""
九步劳动争议咨询系统 - LangGraph 实现

Phase 3 重构版：
- 每个 Agent 直接用 model.invoke()，不再使用 create_agent
- Prompt 分为：全局上下文（所有Agent共享）+ 步骤特有业务逻辑
- 动态注入：从 state 读取当前案件上下文注入到 prompt
- Per-step tools：每步只暴露需要的工具
"""
import json
import re
from typing import Annotated, Dict, List, Literal, Optional, Any, Callable
from datetime import datetime
from operator import add as messages_add

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
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
    serialize_state,
    deserialize_state,
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
你必须在回复的最后一行输出一个 JSON 对象来指定要执行的命令。

### 命令输出格式
当需要跳转到下一步时，输出：
{"tool":"proceed_to_next_step","route":"目标步骤","参数名":"参数值"}

当需要返回上一步时，输出：
{"tool":"back_to_previous_step","step_name":"步骤名称"}

当需要暂停保存时，输出：
{"tool":"pause_and_save"}

当需要追问用户时，输出：
{"tool":"request_missing_info","prompt":"追问内容"}

当需要完成咨询时，输出：
{"tool":"finish_consultation"}

### 可用命令列表
- proceed_to_next_step: 结束当前步骤，进入下一步（必须携带必要的参数）
- back_to_previous_step: 返回上一步修改
- request_missing_info: 追问用户缺失信息
- pause_and_save: 暂停并保存进度
- finish_consultation: 完成咨询
- go_to_step: 跳转到指定步骤

## 状态字段说明
当前案件状态（从 state 中注入）：
- current_step: 当前步骤编号 (1-10)
- case_category: 案由分类（欠薪/开除/工伤/调岗/社保/其他）
- session_id: 会话ID

## 脏数据处理
如果 dirty_steps 包含当前步骤，说明之前的回答已被修改。
你应该告知用户："检测到之前的回答有修改，当前内容已标记为待更新。"

## 严格遵守
- 只使用上面列出的命令格式
- 不要编造不存在的命令
- 回复应当帮助用户完成当前步骤的任务
- 每次回复最多只能包含一个命令
"""


# ============================================================================
# 步骤特有 Prompt（每步独立）
# ============================================================================

STEP_PROMPTS: Dict[str, str] = {
    "step1_selector": """## 本步任务：模式选择

你的任务：欢迎用户，介绍两种咨询模式，引导用户选择。

## 两种咨询模式

### 模式一：律师视频咨询
- 连接值班律师进行一对一视频咨询
- 服务时间：工作日工作时间（周一至周五 8:30-17:30）
- 适用场景：情况紧急、案情复杂需要当面沟通
- 注意：可能需要排队等待

### 模式二：AI智能问答（全流程引导）
- 通过AI引导完成从咨询到文书生成的完整维权流程
- 适用场景：一般性劳动争议、有充足时间系统梳理
- 优势：随时暂停保存、9步完整覆盖

## 回复格式要求（非常重要）
你必须生成包含【文本回复】的消息！格式为：
1. 第一部分：用自然语言向用户介绍两种模式（这是给用户看的）
2. 第二部分：命令输出（在最后一行输出 JSON 命令）

注意：如果用户已经明确表达了选择（如"我想用AI"），你仍然需要用自然语言确认收到用户的选择，
然后在回复末尾输出命令。

## 结束条件
用户明确选择后，输出命令：
{"tool":"proceed_to_next_step","route":"ai_consultation"}

## 命令限制
本步骤可用命令：proceed_to_next_step, request_missing_info, pause_and_save
""",

    "step2_initial": """## 本步任务：问题初判

用户已选择【AI智能问答】。现在需要确定处理路径。

## 三条处理路径

### 路径A：转律师视频
触发条件：
- 用户情况紧急
- 涉及重大金额
- 明确要求律师介入

### 路径B：自由描述案情
触发条件：
- 用户开始描述具体问题
- 表达了明确的争议内容

处理方式：
1. 认真倾听，提取关键信息
2. 识别情感状态（焦虑/愤怒/迷茫）
3. 展示6大案由图标确认

### 路径C：交互式问答
触发条件：
- 用户希望系统化梳理
- 没有明确案情描述

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

## 工具限制
本步骤可用工具：proceed_to_next_step, go_to_step, request_missing_info, back_to_previous_step
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

## 工具限制
本步骤可用工具：proceed_to_next_step, request_missing_info, back_to_previous_step
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

## 案由特殊问题

### 欠薪特殊问题
欠Q1-Q10：
- 欠薪开始时间
- 欠薪月数
- 公司欠薪说明
- 劳动关系状态（stop_fact）
- 工资是否固定
- 欠薪书面证据（stop_fact）
- 最后发薪日
- 公司经营状态
- 是否向劳动监察投诉
- 加班费是否也欠发

### 开除特殊问题
开Q1-Q10：
- 辞退具体日期（stop_fact）
- 辞退理由（stop_fact）
- 书面辞退通知（stop_fact）
- 是否提前30天通知
- 离职交接单签署
- 工作年限（stop_fact）
- 经济补偿金支付
- 2N赔偿金要求
- 处罚会议
- 失业保险申领

### 工伤特殊问题
工Q1-Q10：
- 工伤发生日期（stop_fact）
- 工伤经过（stop_fact）
- 受伤部位（stop_fact）
- 医疗费用
- 工伤认定申请
- 工伤认定决定书
- 劳动能力鉴定
- 工伤期间工资
- 护理情况
- 返岗可能

### 调岗特殊问题
调Q1-Q7：
- 调岗时间
- 调岗性质（stop_fact）
- 新岗位
- 调岗理由
- 书面调岗通知（stop_fact）
- 是否同意调岗
- 工资降低金额

### 社保证据问题
社Q1-Q6：
- 欠缴开始时间
- 欠缴险种（stop_fact）
- 欠缴月数
- 公司是否承认
- 个人部分是否已扣
- 是否向社保局投诉

## 结束条件
5个核心事实全部厘清 → proceed_to_next_step
用户主动要求跳过 → proceed_to_next_step

## 工具限制
本步骤可用工具：proceed_to_next_step, request_missing_info, back_to_previous_step
""",

    "step5_qualification": """## 本步任务：案件定性 + 权益清单生成

基于 step3 和 step4 的回答，生成规范化的案件描述和权益清单。

## 数据输入
你应该从 state 中读取：
- step3_common 的 Q1-Q12 回答
- step4_special 的特殊问题回答
- case_category（主案由）

## 输出要求

### 1. 案件事实描述
生成一段规范化的案件描述：
- 当事人信息（申请人/被申请人）
- 劳动关系基本情况
- 核心争议经过
- 金额计算

### 2. 案由编码（三级）
- 一级：劳动争议
- 二级：劳动合同纠纷 / 工伤保险待遇纠纷 / 社会保险纠纷
- 三级：根据核心诉求确定

### 3. 权益清单
为每个权益项生成：
- right_name: 权益名称
- amount: 金额
- calculation_basis: 计算方式
- legal_basis: 法律依据

### 常见权益计算
- 欠薪：月数 × 月工资
- 违法解除(2N)：年限 × 2 × 月工资（最高12年）
- 经济补偿金(N)：年限 × 月工资
- 未签合同双倍工资：11个月 × 月工资

## 展示格式
向用户展示：
1. 案件概述（规范化描述）
2. 案由编码
3. 权益清单表格
4. 法律依据索引

## 用户确认
展示完毕后询问："以上内容是否准确？如有误请指出。"

## 结束条件
用户确认后
调用 proceed_to_next_step，携带：qualification（含案件事实、案由编码、权益清单、法律依据）

## 工具限制
本步骤可用工具：proceed_to_next_step, request_missing_info, back_to_previous_step
""",

    "step6_evidence": """## 本步任务：证据攻略

基于 case_category 从证据库加载对应证据清单。

## 数据输入
从 state 读取：
- case_category
- qualification（案件定性）

## 证据清单结构（按3级分类）

### tier 1（最强证据）
证明力最强，仲裁必不可少
- 劳动合同原件
- 工资银行流水
- 书面辞退通知 / 欠薪证明 等

### tier 2（辅助证据）
补充增强证明力
- 工资条、社保记录
- 微信/钉钉工作记录
- 录音录像 等

### tier 3（兜底证据）
补强证据链
- 入职通知、同事证词
- 事故现场照片 等

## 证据状态标记
引导用户为每项标记：
- A（已有）：已持有，准备上传
- B（可补充）：可以通过努力获取
- C（无法获得）：客观上无法获取

## B类证据获取指引
对于标记为B的证据，提供：
1. 获取步骤
2. 话术模板
3. 替代方案

## 证据完整度评级
- 充分：A类证据≥3个，A+B≥80%
- 基本完整：A类≥2个，或A+B≥60%
- 不完整：A类=1个，或A+B<60%
- 严重缺乏：A类=0

## 结束条件
调用 proceed_to_next_step，携带：
- evidence_items（含状态标记）
- evidence_completeness（评级）

## 工具限制
本步骤可用工具：proceed_to_next_step, upload_evidence, request_missing_info, back_to_previous_step
""",

    "step7_risk": """## 本步任务：风险评估

综合分析案件事实、证据完整度，给出风险提示。

## 风险评估维度

### 1. 时效风险
- 劳动争议仲裁时效1年
- 从知道或应当知道权利被侵害之日起算
- 欠薪：最后一次工资应付之日起算
- 解除：解除之日起算

### 2. 证据风险
- 证据链是否完整
- 关键证据是否缺失
- 证据是否存在伪造风险

### 3. 诉求计算风险
- 金额计算是否有依据
- 是否超过法定标准

### 4. 用人单位抗辩风险
- 已过时效
- 劳动者存在过错
- 已达成和解

### 5. 程序风险
- 仲裁委管辖是否正确
- 是否需要先经调解

## 风险等级
- 高危：时效过期/关键证据全缺/充分抗辩理由
- 中危：部分证据缺失/计算可能偏差
- 低危：证据充分/事实清楚

## 高危醒目标注
以下情况必须高危标注：
- 时效已过或即将届满
- 关键证据全部缺失
- 劳动关系认定有争议

## 输出格式
向用户展示：
1. 综合风险等级
2. 风险点清单（含等级/描述/建议）
3. 证据链评估
4. 总体建议

## 结束条件
调用 proceed_to_next_step，携带：
- risk_assessment（level, risk_points, evidence_chain_evaluation, recommendations）

## 工具限制
本步骤可用工具：proceed_to_next_step, request_missing_info, back_to_previous_step
""",

    "step8_documents": """## 本步任务：文书生成

基于案件信息、证据清单、权益清单，生成仲裁申请书。

## 数据输入
从 state 读取：
- qualification（案件事实+权益清单+法律依据）
- evidence_items（证据清单）
- case_category

## 文书模板（仲裁申请书）
标准格式，含：
- 申请人/被申请人信息
- 仲裁请求（逐项列明金额）
- 事实和理由
- 证据清单
- 结尾和日期

## 自动填充
从 state 中提取数据填充模板：
- 申请人信息 ← step3 回答
- 案件事实 ← qualification.case_facts
- 仲裁请求 ← qualification.rights_list
- 证据清单 ← evidence_items

## 智能校验
检测缺失字段并高亮：
- 申请人出生年月
- 被申请人法定代表人
- 具体金额计算依据
- 关键时间节点

## 文书修改
用户可以提问：
- "这个金额怎么计算？" → 解释计算逻辑
- "能帮我修改表述吗？" → 提供修改建议

## 结束条件
调用 proceed_to_next_step，携带：
- document_draft（template_type, content, gaps）

## 工具限制
本步骤可用工具：proceed_to_next_step, request_missing_info, back_to_previous_step
""",

    "step9_roadmap": """## 本步任务：行动路线图

展示三步维权路径：协商 → 调解 → 仲裁

## 三步维权路径

### 第一步：协商
适用：争议金额小、双方愿意协商
成本：无
速度：最快
成功率：约30%
话术：起草书面协商函

### 第二步：调解（推荐）
适用：协商不成、希望快速解决
渠道：工会调解 / 街道调解 / 企业调解
成本：无（免费）
速度：2-4周
成功率：约50%
宿迁市总工会调解热线：0527-843XXXXX

### 第三步：仲裁
适用：调解不成、金额较大
渠道：宿迁市劳动人事争议仲裁委员会
程序：提交申请 → 5日内受理 → 45日内结案
成本：可能收取仲裁费

## 路径推荐
根据 case_category 和证据完整度推荐：
- 欠薪：调解优先（快速）→ 仲裁（先予执行）
- 开除：协商同步 → 调解 → 仲裁
- 工伤：工伤认定先行 → 调解/仲裁

## 办理点信息
宿迁市劳动人事争议仲裁委员会：
- 地址：宿迁市宿城区XX路XX号
- 电话：0527-843XXXXX

宿迁市总工会法律维权部：
- 地址：宿迁市宿城区XX路XX号
- 电话：0527-843XXXXX

## 结束条件
调用 proceed_to_next_step，进入 step10_review

## 工具限制
本步骤可用工具：proceed_to_next_step, back_to_previous_step
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
发送完整案件材料给工会值班律师：
- 案件概述
- 案由分类
- 权益清单
- 证据完整度评级
- 风险评估报告
- 文书草稿

值班律师将在1-3个工作日内回复。

## 自由提问
用户也可以自由输入复核问题。

## 结束条件
用户点击"完成咨询" → finish_consultation
用户选择继续 → proceed_to_next_step（进入路线图）

## 工具限制
本步骤可用工具：proceed_to_next_step, request_lawyer_help, request_missing_info, finish_consultation
""",
}


# ============================================================================
# Per-Step 工具配置
# ============================================================================

STEP_TOOLS: Dict[str, List[Callable]] = {
    "step1_selector": [
        "proceed_to_next_step",
        "request_missing_info",
        "pause_and_save",
    ],
    "step2_initial": [
        "proceed_to_next_step",
        "go_to_step",
        "request_missing_info",
        "back_to_previous_step",
    ],
    "step3_common": [
        "proceed_to_next_step",
        "request_missing_info",
        "back_to_previous_step",
    ],
    "step4_special": [
        "proceed_to_next_step",
        "request_missing_info",
        "back_to_previous_step",
    ],
    "step5_qualification": [
        "proceed_to_next_step",
        "request_missing_info",
        "back_to_previous_step",
    ],
    "step6_evidence": [
        "proceed_to_next_step",
        "upload_evidence",
        "request_missing_info",
        "back_to_previous_step",
    ],
    "step7_risk": [
        "proceed_to_next_step",
        "request_missing_info",
        "back_to_previous_step",
    ],
    "step8_documents": [
        "proceed_to_next_step",
        "request_missing_info",
        "back_to_previous_step",
    ],
    "step9_roadmap": [
        "proceed_to_next_step",
        "back_to_previous_step",
    ],
    "step10_review": [
        "proceed_to_next_step",
        "request_lawyer_help",
        "request_missing_info",
        "finish_consultation",
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

    # 从 state 提取当前步骤的上下文
    current_step = state.get("current_step", 1)
    case_category = state.get("case_category")
    session_id = state.get("session_id", "")
    dirty_steps = state.get("dirty_steps", set())
    completed_steps = state.get("completed_steps", set())

    # 当前步骤是否脏：只有当步骤已经完成又被标记为脏时才算脏
    # 刚进入的步骤（未完成）不算脏
    current_step_num = STEP_NAMES.index(step_name) + 1 if step_name in STEP_NAMES else current_step
    is_dirty = current_step_num in dirty_steps and current_step_num in completed_steps

    # 构建上下文注入字符串
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

    # 注入 step_data（关键步骤的已收集数据）
    step_data = state.get("step_data", {})
    if step_name == "step3_common" and "step2_initial" in step_data:
        # step3 可以看到 step2 的选择结果
        step2_data = step_data.get("step2_initial", {}).get("answers", {})
        if step2_data:
            context_lines.append(f"\nStep2 用户选择：{step2_data}")

    if step_name == "step4_special":
        # step4 可以看到 step3 的完整回答
        if "step3_common" in step_data:
            q_answers = step_data["step3_common"].get("answers", {})
            context_lines.append(f"\nStep3 通用问题回答：")
            for k, v in q_answers.items():
                context_lines.append(f"  {k}: {v}")
        if case_category:
            context_lines.append(f"\n主案由：{case_category}")

    if step_name == "step5_qualification":
        # step5 看到 step3+step4 的完整数据
        for sname in ["step3_common", "step4_special"]:
            if sname in step_data:
                answers = step_data[sname].get("answers", {})
                context_lines.append(f"\n{sname} 回答：")
                for k, v in answers.items():
                    context_lines.append(f"  {k}: {v}")

    if step_name == "step6_evidence":
        # step6 看到案件定性和权益清单
        qual = state.get("qualification")
        if qual:
            context_lines.append(f"\n案件定性：")
            context_lines.append(f"  案由：{qual.get('case_types', [])}")
            rights = qual.get("rights_list", [])
            for r in rights:
                context_lines.append(f"  权益：{r.get('right_name')} = {r.get('amount')}元")

    if step_name == "step7_risk":
        # step7 看到证据完整度
        evidence_items = state.get("evidence_items", [])
        if evidence_items:
            a_count = sum(1 for e in evidence_items if e.get("status") == "A")
            b_count = sum(1 for e in evidence_items if e.get("status") == "B")
            c_count = sum(1 for e in evidence_items if e.get("status") == "C")
            completeness = evaluate_evidence_completeness(evidence_items)
            context_lines.append(f"\n证据状态（已标记）：A={a_count}, B={b_count}, C={c_count}")
            context_lines.append(f"证据完整度：{completeness}")

    if step_name == "step8_documents":
        # step8 看到案件定性和证据
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
        # step9 看到风险评估
        risk = state.get("risk_assessment")
        if risk:
            context_lines.append(f"\n风险等级：{risk.get('level', '未知')}")
            for rp in risk.get("risk_points", [])[:3]:
                if rp.get("is_high_risk"):
                    context_lines.append(f"  ⚠️ 高危：{rp.get('description', '')[:50]}")

    if step_name == "step10_review":
        # step10 看到完整案件摘要
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
# Tool 绑定（per-step）
# ============================================================================

def get_step_tools(step_name: str) -> List[Any]:
    """返回指定步骤可用的工具列表"""
    tool_names = STEP_TOOLS.get(step_name, STEP_TOOLS.get("step1_selector", []))
    all_tools = {
        "proceed_to_next_step": proceed_to_next_step,
        "request_missing_info": request_missing_info,
        "back_to_previous_step": back_to_previous_step,
        "pause_and_save": pause_and_save,
        "check_and_apply_dirty": check_and_apply_dirty,
        "finish_consultation": finish_consultation,
        "go_to_step": go_to_step,
        "upload_evidence": upload_evidence,
        "request_lawyer_help": request_lawyer_help,
    }
    return [all_tools[name] for name in tool_names if name in all_tools]


# ============================================================================
# 工具定义
# ============================================================================

@tool
def go_to_step(runtime: ToolRuntime, step_name: str, reason: str = "") -> str:
    """跳转到指定步骤（仅用户主动跳转时使用）"""
    target_step = STEP_NAMES.index(step_name) + 1
    dirty = get_dirty_range(target_step)
    display = STEP_DISPLAY_NAMES.get(step_name, step_name)
    msg = f"已跳转至 [{display}]。"
    if reason:
        msg += f" 原因：{reason}"
    msg += " 后续步骤已标记为待更新。"
    return msg


@tool
def proceed_to_next_step(
    runtime: ToolRuntime,
    step_answers: Dict[str, Any],
    extra_data: Optional[Any] = None,
) -> Command:
    """
    当前步骤完成，携带数据进入下一步。

    重要：step_name 由系统根据 current_step 自动确定，无需传入。
    """
    import json as _json

    current_step_num = runtime.state.get("current_step", 1)
    current_step_name = STEP_NAMES[current_step_num - 1]
    target_step_num = current_step_num + 1

    # 兼容 extra_data 可能是 JSON 字符串的情况
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

    # 如果是 step2 完成，提取 case_category 并写入 state
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

    # 路由由 current_step 决定，这里只返回 state updates
    if target_step_num > 10:
        return updates  # graph 会自然结束
    return updates


@tool
def request_missing_info(runtime: ToolRuntime, prompt: str) -> str:
    """追问用户缺失信息（不跳转步骤）"""
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

    # 路由由 current_step 决定，这里只返回 state updates
    return {
        "current_step": target_step_num,
        "dirty_steps": existing_dirty,
        "last_updated": datetime.now().isoformat(),
    }


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
# 文本命令解析器（替代 bind_tools）
# ============================================================================

def parse_text_command(text: str) -> tuple[Optional[str], Optional[Dict], Optional[str]]:
    """
    从 LLM 文本响应中解析命令。

    支持三种格式：
    1. [TOOL:tool_name:{"arg1": "value1", ...}]
    2. {"tool_name": "tool_name", "parameters": {"arg1": "value1", ...}}
    3. {"tool": "tool_name", "route": "value1", ...} (flattened args)

    返回：(tool_name, args_dict, error_message)
    如果没有找到命令格式，返回 (None, None, None)
    """
    # 格式1: [TOOL:tool_name:args_json]
    pattern1 = r'\[TOOL:(\w+):(\{.*?\})\]'
    match1 = re.search(pattern1, text, re.DOTALL)
    if match1:
        tool_name = match1.group(1)
        args_json = match1.group(2)
        try:
            args = json.loads(args_json)
            return (tool_name, args, None)
        except json.JSONDecodeError as e:
            return (None, None, f"JSON解析错误: {e}")

    # 格式2: {"tool_name": "...", "parameters": {...}}
    pattern2 = r'\{"tool_name"\s*:\s*"(\w+)"\s*,\s*"parameters"\s*:\s*(\{.*?\})\}'
    match2 = re.search(pattern2, text, re.DOTALL)
    if match2:
        tool_name = match2.group(1)
        args_json = match2.group(2)
        try:
            args = json.loads(args_json)
            return (tool_name, args, None)
        except json.JSONDecodeError as e:
            return (None, None, f"JSON解析错误: {e}")

    # 格式3: 直接解析整个文本为 JSON，取出 tool 和其他字段
    # 尝试提取 {...} JSON 块
    json_pattern = r'\{[^{}]*\}'
    for match in re.finditer(json_pattern, text):
        json_str = match.group()
        try:
            obj = json.loads(json_str)
            if 'tool' in obj and isinstance(obj.get('tool'), str):
                tool_name = obj['tool']
                args = {k: v for k, v in obj.items() if k != 'tool'}
                return (tool_name, args, None)
        except json.JSONDecodeError:
            continue

    return (None, None, None)


def execute_tool_command(
    tool_name: str,
    tool_args: Dict[str, Any],
    state: Dict,
    tools: List[Any],
) -> tuple[Any, Optional[Dict], Optional[str]]:
    """
    执行解析出的工具命令。

    返回：(result, command_update, error_message)
    - result: 工具执行结果（用于展示给用户）
    - command_update: 如果返回 Command 的 update 字典，则包含路由信息
    - error_message: 错误信息
    """
    # 找到对应工具
    matched_tool = None
    for t in tools:
        if t.name == tool_name:
            matched_tool = t
            break

    if matched_tool is None:
        return (None, None, f"未知工具: {tool_name}")

    # 创建模拟 runtime 以传递 state
    class MockRuntime:
        pass
    mock_runtime = MockRuntime()
    mock_runtime.state = state

    # 对于 proceed_to_next_step，映射 flat args 到 step_answers
    if tool_name == "proceed_to_next_step":
        # 如果有 route, case_category 等参数，包装成 step_answers
        if "step_answers" not in tool_args and ("route" in tool_args or "case_category" in tool_args):
            tool_args = {"step_answers": tool_args}

    # 调用工具
    try:
        tool_result = matched_tool.func(runtime=mock_runtime, **tool_args)

        # 检查是否返回 Command 或 plain dict
        if isinstance(tool_result, Command):
            if hasattr(tool_result, "goto") and tool_result.graph == Command.PARENT:
                return (None, tool_result.update, tool_result.goto)
            return (str(tool_result), None, None)
        if isinstance(tool_result, dict):
            # plain dict - 用于 current_step 驱动的路由，只取 update
            return (None, tool_result, None)
        return (str(tool_result), None, None)

    except Exception as e:
        return (None, None, f"工具执行错误: {e}")


# ============================================================================
# Step Node 构建（使用文本命令解析替代 bind_tools）
# ============================================================================

def _build_step_node(step_name: str):
    """
    为指定步骤构建一个 node 函数。
    使用文本格式接收 LLM 命令，替代 bind_tools 方案。
    """
    from langgraph.errors import ParentCommand
    from langchain_core.messages import ToolMessage

    tools = get_step_tools(step_name)

    def node(state: ConsultationState) -> Dict:
        # 0. 自动加载证据清单（step6 首次进入时）
        return_dict = {}
        if step_name == "step6_evidence" and not state.get("evidence_items"):
            case_category = state.get("case_category")
            if case_category and case_category not in ("__VIDEO_CALL__",):
                items = get_evidence_checklist(case_category)
                if items:
                    return_dict["evidence_items"] = items

        # 1. 动态构建带完整上下文的 system prompt
        system_prompt = build_step_system_prompt(step_name, state)

        # 2. 获取消息历史
        all_messages = state.get("messages", [])
        if not all_messages:
            # 即使没有消息，也先返回证据清单（如果有的话）
            if return_dict:
                return return_dict
            return {"messages": []}

        # 3. 构造消息历史：SystemMessage(prompt) + 用户消息
        messages_for_model = [
            SystemMessage(content=system_prompt),
        ] + all_messages

        # 4. 调用 LLM 生成文本响应（不使用 bind_tools）
        ai_response = model.invoke(messages_for_model)
        ai_content = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)

        # 5. 解析文本中的命令
        tool_name, tool_args, parse_error = parse_text_command(ai_content)

        if parse_error:
            # JSON 解析错误，返回错误信息
            return {"messages": [AIMessage(content=ai_content + f"\n\n[系统提示: {parse_error}]")]}

        if tool_name is None:
            # 没有命令，直接返回 AI 回复
            return {"messages": [ai_response]}

        # 6. 执行命令
        result, command_update, command_goto = execute_tool_command(
            tool_name, tool_args or {}, state, tools
        )

        # 构建 AI 回复内容
        response_content = ai_content
        if result:
            response_content += f"\n\n{result}"

        # 关键修复：无论有没有 command_goto，都要合并 command_update
        # 路由现在完全由 current_step 决定，工具执行后的 state 更新必须生效
        # 同时保留自动加载的 evidence_items
        final_dict = {"messages": [AIMessage(content=response_content)]}
        if command_update:
            final_dict.update(command_update)
        # 如果 step6 自动加载了 evidence_items，保留它
        if return_dict.get("evidence_items") and "evidence_items" not in final_dict:
            final_dict["evidence_items"] = return_dict["evidence_items"]
        return final_dict

    return node


# ============================================================================
# 证据初始化 Node（step6 专用：加载证据清单）
# ============================================================================

def _build_evidence_init_node(step_name: str = "step6_evidence"):
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
# 路由函数：读取节点返回的 goto 字段决定下一步
# ============================================================================

def _route_to_next(state: ConsultationState) -> str:
    """
    路由函数：根据 current_step 决定下一步（唯一真实来源）。

    goto 字段不再用于路由（因为它会跨迭代持久化，导致路由错误）。
    每次都严格基于 current_step 的当前值决定下一步。
    """
    current = state.get("current_step", 1)
    if current < len(STEP_NAMES):
        return STEP_NAMES[current - 1]  # current_step 是 1-based
    return END


# ============================================================================
# StateGraph 构建
# ============================================================================

def create_consultation_graph():
    """
    构建九步咨询系统 StateGraph。

    架构变化（对比 Phase 2）：
    - 每个 node 直接用 model.invoke() + 动态 SystemMessage
    - 不再使用 create_agent
    - prompt = 全局上下文 + 步骤特有逻辑 + 当前案件状态
    - 每步工具集合不同
    """
    workflow = StateGraph(
        ConsultationState,
        input_schema=ConsultationInput,
    )

    # 添加所有步骤节点
    for step_name in STEP_NAMES:
        workflow.add_node(step_name, _build_step_node(step_name))

    # 边：起点 → step1
    workflow.add_edge(START, STEP_NAMES[0])

    # 条件路由：每个步骤之后根据 current_step 决定下一步
    for step_name in STEP_NAMES:
        workflow.add_conditional_edges(
            step_name,
            _route_to_next,
            {
                **{name: name for name in STEP_NAMES},
                END: END,
            },
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


# ============================================================================
# Debug 入口
# ============================================================================

if __name__ == "__main__":
    from langchain_core.messages import HumanMessage

    print("=" * 60)
    print("九步咨询系统 v2.0 - 动态 Prompt 重构版")
    print("=" * 60)

    initial = create_initial_state("debug-session-001")
    print(f"\n初始状态：step={initial['current_step']}, session={initial['session_id']}")

    graph = get_consultation_graph()

    config = {
        "configurable": {"thread_id": "debug-001"},
        "recursion_limit": 100,
    }

    print("\n" + "=" * 60)
    print("测试 Step1: 模式选择")
    print("=" * 60)

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="我想咨询劳动争议问题")],
            **initial,
        },
        config=config,
    )

    for msg in result.get("messages", []):
        if hasattr(msg, "content") and msg.content:
            print(f"\n[AI] {msg.content[:300]}")
