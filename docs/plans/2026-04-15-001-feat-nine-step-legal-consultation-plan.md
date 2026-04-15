---
title: "feat: 九步引导式法律咨询系统"
type: feat
status: active
date: 2026-04-15
origin: docs/brainstorms/2026-04-15-phase2-rights-protection-requirements.md
---

# 九步引导式法律咨询系统

## Overview

将宿迁工会劳动争议咨询系统从当前的单轮问答后端（L2），升级为九步引导式全流程智能咨询应用。核心变化：从"自由对话获取建议"转向"结构化采集 + 智能化辅助 + Agentic 弹性"。

**Origin decisions carried forward:**
- LangGraph 九步主流程，每步 = `create_agent` + handoffs（hybrid skeleton + agentic）
- 先从6大高频分类（欠薪/开除/工伤/调岗/社保/其他）开始，300+案由后续迭代
- 12个通用问题已确认（Q1-Q12）
- 证据本地文件存储；文书国家标准格式；办理点先用省级通用信息

## Architecture

### 混合架构：StateGraph骨架 + Agent节点

```
┌─────────────────────────────────────────────────────┐
│           主 StateGraph（固定骨架 + 业务保证）           │
│                                                     │
│  START → [step1_selector] → [step2_initial] →        │
│  [step3_common_questions] → [step4_special] →       │
│  [step5_qualification] → [step6_evidence] →         │
│  [step7_risk] → [step8_documents] →                │
│  [step9_roadmap] → [step10_review] → END            │
│                      ↑         ↑                     │
│              任意前序步骤 ←──┘  (backtrack handoff)  │
└─────────────────────────────────────────────────────┘
              ↓ each step = create_agent + tools
┌─────────────────────────────────────────────────────┐
│  Agent内部：LLM驱动问题生成 + 追问循环 + 动态停止        │
│  Agent外部：固定骨架保证业务完整性                      │
│  Handoffs：tools驱动跨步骤跳转                        │
└─────────────────────────────────────────────────────┘
```

### 状态设计

```python
class ConsultationState(TypedDict):
    # 消息累积（不变）
    messages: Annotated[list[AnyMessage], operator.add]

    # === 九步核心 ===
    current_step: Annotated[int, max]          # 1-10，当前步骤
    completed_steps: set[int]                  # 已完成步骤集合
    step_data: dict[str, StepData]            # 每步采集的数据 {step_name: data}
    dirty_steps: set[int]                     # 需重算的脏步骤

    # === 案件核心 ===
    case_category: str                        # 6大分类之一
    case_types: list[str]                     # 案由列表（单一或组合）
    case_facts: str                           # AI生成的案件事实描述
    rights_list: list[RightItem]               # 权益清单（仲裁请求+金额）
    risk_assessment: RiskAssessment           # 风险提示

    # === 证据体系 ===
    evidence_items: list[EvidenceItem]        # 证据清单（含A/B/C状态）
    evidence_files: dict[str, FileRef]        # 上传文件引用

    # === 文书 ===
    document_draft: str                       # 生成的文书内容
    document_gaps: list[str]                  # 高亮的不完整字段

    # === 元数据 ===
    session_id: str
    started_at: datetime
    last_updated: datetime
    member_id: Optional[str]
    resume_token: Optional[str]               # 用于保存进度的断点token

class StepData(TypedDict):
    answers: dict[str, Any]                  # 问题→回答
    status: Literal["in_progress", "completed", "dirty"]
    completed_at: Optional[datetime]
    extra: dict[str, Any]                    # 步骤特有数据

class EvidenceItem(TypedDict):
    id: str
    name: str                                # 证据名称
    category: Literal["必备", "加强"]         # 第一/第二优先级
    tier: int                                # 1=最强证据 2=辅助 3=兜底
    status: Literal["A", "B", "C"]           # A=已有 B=可补充 C=无法取得
    status_reason: Optional[str]             # 状态说明
    guidance: Optional[str]                   # 获取指引（话术模板等）
    uploaded_file_refs: list[str]            # 上传文件ID列表

class RightItem(TypedDict):
    right_name: str                           # 权利名称
    amount: Optional[float]                   # 金额
    calculation_basis: str                     # 计算依据
    priority: int                            # 优先级

class RiskAssessment(TypedDict):
    level: Literal["高", "中", "低"]
    risk_points: list[RiskPoint]
    mitigation_suggestions: list[str]

class RiskPoint(TypedDict):
    type: str                                 # 时效过期/证据链断裂/诉求计算错误
    description: str
    is_high_risk: bool
    reason: str
```

### Agent 工具设计

每个步骤的 agent 配备以下标准 tools + 步骤特有 tools：

```python
# === 所有步骤通用 ===
@tool
def go_to_step(step_name: str, step_data: dict) -> Command:
    """跳转到指定步骤，标记当前步骤为dirty"""
    # 1. 更新 completed_steps
    # 2. 标记 dirty_steps = {N+1, ..., 10}
    # 3. Command(goto=step_name, graph=PARENT)
    pass

@tool
def request_missing_info(prompt: str) -> str:
    """追问用户缺失信息（不跳转，继续当前步骤）"""
    pass

@tool
def proceed_to_next_step(data: dict) -> Command:
    """当前步骤完成，携带数据进入下一步"""
    pass

@tool
def pause_and_save() -> str:
    """保存当前进度，返回resume_token"""
    pass

# === 证据步骤特有 ===
@tool
def upload_evidence(file_ref: str, evidence_id: str) -> str:
    """关联文件到证据项"""
    pass

@tool
def get_evidence_guidance(evidence_id: str) -> str:
    """获取证据收集指引（话术模板/操作指南）"""
    pass

@tool
def generate_legal_document(template_type: str) -> str:
    """生成法律文书草稿"""
    pass
```

### Handoff 协议

Agent 之间的跳转通过 `Command(goto=node_name, update={...})` 实现：

```python
# step3 完成后跳转 step4
@tool
def proceed_to_special_questions(data: dict) -> Command:
    return Command(
        goto="step4_special_questions",
        update={
            "step_data": {...step3_data...},
            "current_step": 4,
            "completed_steps": completed_steps | {3},
            "dirty_steps": dirty_steps | {4,5,6,7,8,9,10}
        },
        graph=Command.PARENT
    )

# step5 可跳转回 step3 修改通用问题
@tool
def back_to_common_questions(reason: str) -> Command:
    return Command(
        goto="step3_common_questions",
        update={
            "dirty_steps": dirty_steps | {3,4,5,6,7,8,9,10},
            "current_step": 3
        },
        graph=Command.PARENT
    )
```

### 动态停止条件（Step 4）

Step 4 的特殊问题追问，在每个回答后调用 LLM 判断：

```python
def should_stop_special_questions(answers: dict, case_facts_so_far: str) -> bool:
    """LLM判断：核心事实是否已厘清？"""
    stop_check_prompt = f"""
    基于已收集的信息：
    {case_facts_so_far}

    判断：是否已厘清以下核心事实？
    1. 用人单位名称
    2. 入职时间
    3. 劳动关系状态
    4. 核心争议内容
    5. 涉及金额（如适用）

    如以上5项全部明确，返回 STOP
    如仍有模糊项，返回 CONTINUE + 列出缺失项
    """
    response = llm.invoke([HumanMessage(content=stop_check_prompt)])
    return "STOP" in response.content
```

### 回退重算协议

当用户修改了 step N 的数据：

```
Step N 数据变更
    ↓
dirty_steps = {N, N+1, ..., 10}
    ↓
进入 Step N+1 时检测 dirty flag
    ↓
弹出确认："您修改了Step N的数据，是否重新生成后续内容？"
    ↓
[重新生成] → 清空 dirty，重新计算
[保留原内容] → 仅清除 dirty 标记，保留已有数据
```

---

## Implementation Phases

### Phase 1: 状态与骨架（Week 1-2）

**目标：** 搭建九步 StateGraph 骨架 + 新状态设计

#### 1.1 新状态设计
- [ ] 重构 `AgentState` → `ConsultationState`
- [ ] 定义 `StepData`, `EvidenceItem`, `RightItem`, `RiskAssessment` 等子类型
- [ ] 添加 `dirty_steps` 追踪机制
- [ ] 添加 `resume_token` 保存/恢复机制

#### 1.2 主骨架实现
- [ ] 创建 `consultation_graph.py`，基于 `legal_supervisor.py` 的 `create_agent` 模式
- [ ] 定义10个步骤节点：`step1_selector`, `step2_initial`, `step3_common`, `step4_special`, `step5_qualification`, `step6_evidence`, `step7_risk`, `step8_documents`, `step9_roadmap`, `step10_review`
- [ ] 实现标准 tools：`go_to_step`, `proceed_to_next_step`, `request_missing_info`, `back_to_step`
- [ ] 实现 `dirty_steps` 检测逻辑
- [ ] 实现回退重算确认流程

#### 1.3 测试骨架
- [ ] 用假数据测试10步顺序流转
- [ ] 测试从 Step 7 回退到 Step 3 的 dirty 标记
- [ ] 测试 `pause_and_save` + `resume_token` 恢复

**交付物：** 可顺序流转的10步骨架，状态完整追踪

---

### Phase 2: 步骤逻辑实现（Week 3-6）

**目标：** 完成每步的 agent prompt + tools + 业务逻辑

#### 2.1 Step 1-2：入口与初判
- [ ] **Step 1 (`step1_selector`)**：律师视频 / AI问答 二选一
  - 律师视频：返回路由标识（外部接入点）
  - AI问答：进入 Step 2
- [ ] **Step 2 (`step2_initial`)**：三路径
  - 路径A（找律师视频）：路由标识
  - 路径B（自述案情）：文本输入框 → answerer 追问厘清
  - 路径C（交互问答）：6个诉求图标 → 进入 Step 3

#### 2.2 Step 3：通用12问
- [ ] 实现 Q1-Q12 的 prompt（已确认内容）
- [ ] 实现各类输入控件的 prompt 映射：
  - 点选 → Radio/Checkbox prompt
  - 日历 → Date prompt + "记不清"
  - 下拉 → Dropdown prompt（含新业态岗位）
  - 数字 → Number prompt
- [ ] 实现金额引导计算器 prompt（加班费/经济补偿金）
- [ ] 12问全部完成 → 进入 Step 4

#### 2.3 Step 4：特殊问题 + 动态停止
- [ ] 构建6大分类的个性问题库（每类 5-15 题）
- [ ] 实现"根据通用问题答案筛选特殊问题"的 prompt
- [ ] 实现 `should_stop_special_questions()` 动态停止判断
- [ ] 多重案由优先级排序逻辑

#### 2.4 Step 5：案件定性
- [ ] 实现案件事实描述生成 prompt（来自 SUMMARIZER_PROMPT 演进）
- [ ] 实现案由编码（三级案由）匹配 prompt
- [ ] 实现权益清单生成 prompt（含金额计算引导）
- [ ] 实现法律依据索引 prompt（链接到 data/民法典.md）

#### 2.5 Step 6：证据攻略
- [ ] 迁移现有 DETAILER_PROMPT 的3级证据分类
- [ ] 实现证据清单匹配（根据案由加载对应证据）
- [ ] 实现 A/B/C 状态标记 prompt
- [ ] 实现证据收集指引生成（话术模板、《劳动关系证明函》等）
- [ ] 实现证据上传 tool（本地上传 → 文件ID）
- [ ] 实现证据审核反馈 prompt（基于上传文件内容判断）
- [ ] 实现证据完整度评估（充分/不完整/缺乏/严重缺乏）

#### 2.6 Step 7：风险提示
- [ ] 实现风险分析 prompt（综合事实清晰度+证据+对方抗辩）
- [ ] 实现风险点提取（时效/证据链/计算错误等）
- [ ] 实现高风险醒目标注 prompt
- [ ] 实现规避建议生成 prompt

#### 2.7 Step 8：文书生成
- [ ] 准备国家标准格式的《仲裁申请书》《调解申请书》模板
- [ ] 实现自动填充 prompt
- [ ] 实现智能校验 + 高亮标注 prompt
- [ ] 实现补充问题生成 prompt
- [ ] 实现文书修改建议 prompt（基于会员提问）

#### 2.8 Step 9：行动路线图
- [ ] 实现流程图展示 prompt（协商→调解→仲裁）
- [ ] 实现各步骤详细指引 prompt
- [ ] 实现办理点信息展示（暂用省级通用信息）
- [ ] 实现工会调解推荐 prompt（适用案件判断）

#### 2.9 Step 10：求助复核
- [ ] 实现预设提示词模板（5-10个）
- [ ] 实现案件打包格式（JSON/markdown）
- [ ] 实现一键求助律师 tool（API POST 占位）
- [ ] 实现外部 AI 复核接入 prompt

**交付物：** 完整10步可用的 agent 系统

---

### Phase 3: 数据基础设施（Week 4-8，并行）

**目标：** 建立支撑九步的底层数据

- [ ] 构建6大高频分类（欠薪/开除/工伤/调岗/社保/其他）的案由树
- [ ] 构建通用12问的 structured data（question_id → prompt → input_type → validation）
- [ ] 构建6大分类各自的特殊问题库（question_id → trigger_conditions → prompt）
- [ ] 构建证据清单数据库（evidence_id → name → category → tier → description → guidance_template）
- [ ] 准备《仲裁申请书》《调解申请书》模板文件
- [ ] 准备证据话术模板库（10-20个）
- [ ] 准备《要求出具劳动关系证明的函》等法律文书草稿

---

### Phase 4: 集成测试与优化（Week 7-10）

**目标：** 端到端测试 + 性能优化

- [ ] 端到端流程测试（从 Step 1 到 Step 10）
- [ ] 回退场景测试（修改前序步骤 → 验证脏标记重算）
- [ ] 断点保存/恢复测试
- [ ] 证据上传 + 审核反馈测试
- [ ] 文书生成 + 高亮测试
- [ ] LLM 输出稳定性测试（温度=0，多次运行一致性）
- [ ] 并发会话测试（MemorySaver 隔离性）

---

## State Lifecycle Risks

### 风险1：脏标记扩散
当用户在 Step 3 修改数据，Step 4-10 全部标记 dirty，如果用户反复修改，可能导致：
- 下游数据反复重算，浪费 token
- 用户体验碎片化

**缓解：** dirty 标记仅在用户"确认修改"后才触发重算，不在每次编辑时触发

### 风险2：证据文件丢失
证据上传到本地文件，但 session 过期后文件仍在磁盘

**缓解：** 在文档导出完成后（或 session 过期7天后）触发清理 job

### 风险3：Agent 循环
步骤内追问可能导致 Agent 无限循环（用户反复答错）

**缓解：** `request_missing_info` 设置 max_loop=3，超出后强制转向 `pause_and_save`

---

## System-Wide Impact

### 交互图（主要变化）

| 操作 | 触发的模块 |
|---|---|
| 用户进入 AI问答 | step1_selector → step2_initial |
| step3 回答触发 dirty | step4-10 标记 dirty，下次进入时触发重算确认 |
| 证据上传 | step6_evidence 更新 evidence_files |
| 文书生成 | step8 从 step3-7 读取数据，输出 document_draft |
| 保存退出 | 所有 step_data + evidence_files 写入持久化存储 |

### 错误传播

| 错误类型 | 处理方式 |
|---|---|
| LLM API 超时 | 降级为静态 FAQ 回复 + `pause_and_save` |
| LLM JSON 解析失败 | 使用 `repair_json` 或降级为纯文本 |
| 证据上传失败 | 返回具体错误提示，保留原状态 |
| 文件存储满 | 返回错误，不丢失已有数据 |

---

## Acceptance Criteria

### 功能验收
- [ ] 用户从首页进入 AI问答，可顺序完成全部10步
- [ ] 在任意步骤可跳转回任意前序步骤，dirty 标记正确
- [ ] 12个通用问题全部支持点选/下拉/日历输入
- [ ] 特殊问题根据案由动态生成，达到条件后自动停止
- [ ] 证据清单根据案由匹配，A/B/C 状态标记功能可用
- [ ] 证据上传文件持久化到本地，关联到证据项
- [ ] 证据审核反馈生成内容与上传文件相关
- [ ] 文书模板自动填充，缺失字段高亮
- [ ] 行动路线图展示协商→调解→仲裁流程
- [ ] `pause_and_save` 生成 resume_token，可恢复会话
- [ ] "求助律师"打包数据格式正确

### 非功能验收
- [ ] 30分钟内完成从进门到文书生成的全流程（正常情况）
- [ ] LLM 温度=0 时，相同输入多次运行输出一致性 ≥ 95%
- [ ] 端到端 token 消耗控制在合理范围（待压测后定义基线）

---

## Dependencies

| 依赖 | 类型 | 说明 |
|---|---|---|
| LangChain ≥ 1.2.10 | 框架 | `create_agent` API |
| LangGraph | 框架 | StateGraph + Command |
| FastAPI | 框架 | API 服务层 |
| 本地文件存储 | 基础设施 | 证据文件持久化 |
| 案由分类数据 | 数据 | Phase 3 构建 |
| 问题库数据 | 数据 | Phase 3 构建 |
| 证据清单数据 | 数据 | Phase 3 构建 |
| 文书模板 | 数据 | Phase 3 构建 |

---

## Deferred to Later

| 项目 | 原因 | 后续阶段 |
|---|---|---|
| 300+ 案由扩展 | 先 MVP 6大分类 | Phase 3+ |
| Word/PDF 导出 | 暂不实现 | Phase 3+ |
| 文书手动编辑 | 暂不实现 | Phase 3+ |
| 宿迁本地办理点数据 | 暂无数据 | 业务方提供后 |
| 律师端 API 接入 | 暂用占位 | 外部系统对接时 |
| 视频通话集成 | 暂不实现 | 外部系统对接时 |

---

## Next Steps

→ `/ce:work` 开始 Phase 1：状态设计与主骨架实现
