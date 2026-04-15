---
title: "feat: Phase 2 - 九步步骤业务逻辑实现"
type: feat
status: active
date: 2026-04-15
origin: docs/brainstorms/2026-04-15-phase2-rights-protection-requirements.md
---

# Phase 2: 九步步骤业务逻辑实现

## Overview

基于 Phase 1 骨架，在 `consultation_graph.py` 中将 10 个步骤的英文 skeleton prompt 替换为完整业务逻辑 prompt，并实现各步骤特有的数据模型和工具函数。

**继承自 origin 的关键决策：**
- 每步 = `create_agent` + 标准 tools（已骨架实现）
- 跨步骤跳转由 `Command(goto=..., graph=Command.PARENT)` 实现
- `dirty_steps` 支撑回退重算协议
- 先从6大高频分类（欠薪/开除/工伤/调岗/社保/其他）开始

## Technical Approach

### 复用资产

| 现有资源 | 可用于 |
|---|---|
| `DETAILER_PROMPT` 3级证据分类 | step6_evidence 证据清单 |
| `SUMMARIZER_PROMPT` 案情总结 | step5_qualification 案件描述 |
| `ANSWERER_PROMPT` 追问模式 | step3_common 12问交互 |
| `EXTRACTOR_PROMPT` 情感/诉求提取 | step2_initial 案由判断 |
| Phase 1 骨架（7个标准 tools） | 全部步骤 |

### 各步骤实现要点

#### Step 1 (`step1_selector`) — 模式选择
- 实现两个入口的 prompt：律师视频（仅返回标识）/ AI问答
- 律师视频路径：返回 `{"route": "video_call", "available": <bool>"}`
- AI问答路径：进入 step2_initial

#### Step 2 (`step2_initial`) — 问题初判
- **路径A（找律师视频）**：返回视频路由标识
- **路径B（自述案情）**：引导用户自由描述，触发 `request_missing_info` 追问
- **路径C（交互问答）**：展示6个诉求图标（欠薪/开除/工伤/调岗/社保/其他），用户选择后进入 step3_common
- 复用 `EXTRACTOR_PROMPT` 的情感/诉求提取逻辑判断用户选择的类别

#### Step 3 (`step3_common`) — 12个通用问题
- **实现策略**：使用 `request_missing_info` 逐题追问，每题仅问1-2个
- 12问内容（已确认）：
  - Q1 就业状态（点选）/ Q2 离职时间（日历+记不清）/ Q3 劳动合同（点选）/ Q4 月薪（数字）/ Q5 工资发放（点选）/ Q6 社保（点选）/ Q7 岗位（下拉含新业态）/ Q8 入职时间（日历+记不清）/ Q9 工时（点选）/ Q10 诉求（多选）/ Q11 金额（数字）/ Q12 维权结果（点选）
- **输入控件映射**：通过 prompt 指定输入类型，前端据此渲染控件
- **Q12 完成后**：调用 `proceed_to_next_step` 进入 step4_special，数据携带 Q1-Q12 回答

#### Step 4 (`step4_special`) — 特殊问题 + 动态停止
- **个性问题库**（每类5-15题）：基于6大分类构建
- **动态停止判断**：每回答一题，LLM 判断核心事实是否已厘清（用人单位名称、入职时间、劳动关系状态、核心争议、涉及金额）
- **多重案由排序**：按案由优先级（开除 > 欠薪 > 工伤 > ...）排列特殊问题
- **调用 `proceed_to_next_step`**：事实厘清后携带特殊问题回答进入 step5_qualification

#### Step 5 (`step5_qualification`) — 案件定性
- **案件事实生成**：基于 step3+step4 数据，生成规范描述（复用 SUMMARIZER_PROMPT 模式）
- **案由判定**：LLM 根据描述匹配6大分类 + 三级案由编码
- **权益清单**：根据案由和金额生成 `list[RightItem]`
- **法律依据索引**：链接到 `data/民法典.md` 相关条款
- 用户确认/修改后，调用 `proceed_to_next_step`

#### Step 6 (`step6_evidence`) — 证据攻略
- **证据清单匹配**：根据 step5 的案由，从内置证据库加载对应证据
  - 复用 DETAILER_PROMPT 的3级分类（最强/辅助/兜底）
  - `EvidenceItem` 字段：name, description, category, tier, status, guidance
- **状态标记**：引导用户标记 A/B/C，`evidence_items` 更新到 state
- **证据收集指引**：对 B 类证据生成话术模板/操作指南（写入门 `EvidenceItem.guidance`）
- **证据审核**：LLM 读取用户上传的文件内容，给出针对性反馈
- **完整度评级**：根据 A/B/C 分布判断（充分/不完整/缺乏/严重缺乏）
- **证据上传**（占位）：调用 `upload_evidence` tool（本地上传 → `FileRef`）

#### Step 7 (`step7_risk`) — 风险提示
- **综合分析**：基于 step5（案件事实）+ step6（证据完整度）+ 常见抗辩理由
- **风险点提取**：`RiskPoint` 列表（时效过期/证据链断裂/诉求计算错误）
- **高风险醒目标注**：`is_high_risk=True` 的风险点
- **规避建议**：每个风险点附 `mitigation` 建议

#### Step 8 (`step8_documents`) — 文书生成
- **文书模板**：国家标准格式《仲裁申请书》《调解申请书》（占位：等待法律专业人士审定）
- **自动填充**：基于 step3+step4+step5 数据填充模板占位符
- **智能校验**：检测事实不清晰的字段，填入 `DocumentDraft.gaps`
- **高亮提示**：gap 字段用特殊标记包裹，引导用户补充
- **文书修改建议**：用户提问时，LLM 基于知识库修改/优化文书内容

#### Step 9 (`step9_roadmap`) — 行动路线图
- **流程图**：协商→调解→仲裁（三步）
- **每步详情**：从省级通用数据加载（占位：宿迁本地数据后续填充）
- **工会调解推荐**：适用调解的案件（小额/双方愿意协商），提示工会调解电话

#### Step 10 (`step10_review`) — 求助复核
- **预设提示词模板**：5-10个（如"帮我检查证据是否充分"/"这个金额计算对吗"）
- **案件打包**：将 step3-9 所有数据序列化为 JSON/markdown
- **一键求助律师**：调用 `request_lawyer_help` tool（占位：API POST 到律师端）

---

## Data Model Additions

Phase 1 骨架已定义核心类型，Phase 2 补充：

```python
# consultation_state.py 新增 / 补充

# 6大分类
CASE_CATEGORIES = ["欠薪", "开除", "工伤", "调岗", "社保", "其他"]

# 12个通用问题定义
GENERAL_QUESTIONS: List[QuestionDef] = [
    {"id": "Q1", "text": "您目前的就业状态？", "type": "radio", "options": ["在职", "离职", "待岗"]},
    {"id": "Q2", "text": "离职时间？", "type": "calendar", "options": ["记不清"]},
    # ... Q3-Q12
]

# 特殊问题库（按案由分类，每类5-15题）
SPECIAL_QUESTION_BANKS: Dict[str, List[QuestionDef]] = {
    "欠薪": [...],
    "开除": [...],
    # ...
}

# 证据清单（按案由分类）
EVIDENCE_CHECKLIST: Dict[str, List[EvidenceItem]] = {
    "欠薪": [...],
    "开除": [...],
    # ...
}

# 证据话术模板（10-20个）
EVIDENCE_GUIDANCE_TEMPLATES: Dict[str, str] = {
    "工资流水": "请携带身份证到银行网点办理，...",
    "劳动合同": "可向公司HR申请复印，加盖公章后有效，...",
    # ...
}

# 文书模板占位符
DOCUMENT_TEMPLATES: Dict[str, str] = {
    "仲裁申请书": "申请人：___ \n 被申请人：___ \n 仲裁请求：___",
    "调解申请书": "...",
}

# 预设复核提示词
REVIEW_PROMPT_TEMPLATES: List[str] = [
    "请帮我检查证据清单是否充分",
    "这个赔偿金额计算对吗",
    "我这种情况胜算多大",
]
```

---

## Implementation Phases

### Phase 2.1: 数据基础设施（可并行）

- [ ] 构建6大分类的 `SPECIAL_QUESTION_BANKS`（每类5-15题）
- [ ] 构建 `EVIDENCE_CHECKLIST`（按案由 × 3级分类）
- [ ] 构建 `EVIDENCE_GUIDANCE_TEMPLATES`（话术模板10-20个）
- [ ] 准备 `DOCUMENT_TEMPLATES`（国家标准格式，占位）
- [ ] 构建 `GENERAL_QUESTIONS` 结构化数据（Q1-Q12）

### Phase 2.2: Step 1-2 实现

- [ ] 完善 `step1_selector` prompt（两个入口路由逻辑）
- [ ] 完善 `step2_initial` prompt（三路径 + case_category 判定）

### Phase 2.3: Step 3 实现（12问交互）

- [ ] 实现 `step3_common` 追问循环 prompt
- [ ] 实现输入控件类型的 prompt 映射（前端据此渲染）
- [ ] 实现 `proceed_to_next_step` 携带 Q1-Q12 数据

### Phase 2.4: Step 4 实现（特殊问题 + 动态停止）

- [ ] 实现 `SPECIAL_QUESTION_BANKS` 加载逻辑
- [ ] 实现 `should_stop_special_questions()` 判断函数
- [ ] 实现多重案由优先级排序
- [ ] 实现 `proceed_to_next_step` 携带特殊问题数据

### Phase 2.5: Step 5 实现（案件定性）

- [ ] 实现案件事实描述生成 prompt
- [ ] 实现案由编码匹配 prompt（三级案由）
- [ ] 实现权益清单生成 prompt
- [ ] 实现 `case_facts` / `case_types` / `rights_list` 写入 state

### Phase 2.6: Step 6 实现（证据攻略）

- [ ] 实现证据清单匹配（按 case_types 加载 EVIDENCE_CHECKLIST）
- [ ] 实现 A/B/C 状态标记 prompt
- [ ] 实现证据收集指引生成（调用 EVIDENCE_GUIDANCE_TEMPLATES）
- [ ] 实现证据上传 tool（本地上传 → FileRef → evidence_files）
- [ ] 实现证据审核反馈 prompt
- [ ] 实现证据完整度评估

### Phase 2.7: Step 7 实现（风险提示）

- [ ] 实现风险分析 prompt（综合 step5+step6 数据）
- [ ] 实现风险点提取 + 高风险标注
- [ ] 实现规避建议生成
- [ ] 实现 `risk_assessment` 写入 state

### Phase 2.8: Step 8 实现（文书生成）

- [ ] 实现文书模板加载（DOCUMENT_TEMPLATES）
- [ ] 实现自动填充 prompt
- [ ] 实现智能校验 + gaps 高亮
- [ ] 实现文书修改建议 prompt
- [ ] 实现 `document_draft` 写入 state

### Phase 2.9: Step 9-10 实现（路线图 + 复核）

- [ ] 实现 `step9_roadmap` 流程图展示 prompt
- [ ] 实现办理点信息加载（省级通用数据占位）
- [ ] 实现 `step10_review` 预设提示词模板
- [ ] 实现案件打包格式
- [ ] 实现 `request_lawyer_help` tool（API POST 占位）

---

## System-Wide Impact

### Interaction Graph

| 操作 | 触发的状态变化 |
|---|---|
| step3 Q12 完成 | `step_data["step3_common"]` → 进入 step4 |
| step4 动态停止 | `step_data["step4_special"]` → 进入 step5 |
| step5 确认案由 | `case_types`, `case_facts`, `rights_list` → 进入 step6 |
| step6 标记证据B类 | `EvidenceItem.guidance` 生成话术 → 用户获取指引 |
| step6 证据上传 | `evidence_files[file_id]` 新增 → 审核反馈 |
| step8 文书生成 | `document_draft.content` 填充 → 高亮 gaps |

### 错误传播

| 错误类型 | 处理方式 |
|---|---|
| LLM API 超时 | 降级为静态 FAQ + `pause_and_save` |
| LLM JSON 解析失败 | `repair_json` 或降级纯文本 |
| 证据上传失败 | 返回具体错误，保留原状态 |
| 文书模板缺失 | 返回提示，暂不进入 step8 |

---

## Acceptance Criteria

### 功能验收
- [ ] step3 可完成全部12问，每题正确路由到前端控件类型
- [ ] step4 特殊问题根据案由动态加载，达到条件后自动停止
- [ ] step5 生成案件事实描述、案由编码、权益清单元数据写入 state
- [ ] step6 证据清单根据案由匹配，A/B/C 状态标记功能可用
- [ ] step6 证据上传后，审核反馈内容与上传文件相关
- [ ] step7 生成风险评估，高风险醒目标注
- [ ] step8 文书自动填充，缺失字段高亮
- [ ] step9 展示三步维权路线
- [ ] step10 提供预设提示词 + 一键求助律师

### 端到端
- [ ] 用户从 step1 到 step10 完整流转（正常情况）
- [ ] step6 回退到 step3 修改后，dirty 标记触发重新生成
- [ ] `pause_and_save` → resume 恢复正确步骤

---

## Dependencies

| 依赖 | 类型 | 说明 |
|---|---|---|
| Phase 1 骨架 | 基础 | consultation_graph.py 已实现 |
| `repair_json` | 库 | 处理 LLM JSON 输出 |
| `EVIDENCE_GUIDANCE_TEMPLATES` | 数据 | 10-20个话术模板（Phase 2.1 构建） |
| `DOCUMENT_TEMPLATES` | 数据 | 国家标准格式文书（占位待审定） |
| 本地文件存储 | 基础设施 | 证据文件上传路径配置 |

---

## Deferred to Phase 3

| 项目 | 原因 |
|---|---|
| 300+ 案由扩展 | Phase 2 仅6大分类 |
| Word/PDF 导出 | 暂不实现 |
| 文书手动编辑 | 暂不实现 |
| 宿迁本地办理点数据 | 暂无，Phase 2 用省级通用数据 |
| 律师端 API 接入 | 占位实现 |
| 视频通话集成 | 暂不实现 |

---

## Next Steps

→ `/ce:work` 开始 Phase 2.1：数据基础设施构建（特殊问题库 + 证据清单库）
