# AI 聊天与向导双向联动系统设计文档

> 生成日期: 2026-04-14
> 版本: v1.0
> 关联项目: 工会劳动维权 AI 引导系统

---

## 一、设计目标

将 AI 聊天窗口从仅在 Step 9 使用的独立模块，升级为贯穿全部 9 个步骤的一等公民。通过双向联动机制，实现：

- **AI → 向导**: AI 分析完成后，通过建议卡片（确认/忽略）将推断结果回填到向导表单
- **向导 → AI**: 每次步骤完成时，将当前步骤数据同步到 AI 上下文，供 AI 分析
- **对话式交互**: AI 在侧边栏中以对话形式呈现分析结果，而非结构性表格

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        React Web App                        │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │       向导区域 (左)       │  │     AI聊天侧边栏 (右)    │  │
│  │                         │  │                         │  │
│  │  StepWizard             │  │  AIChatPanel            │  │
│  │  StepContent            │  │  - 对话历史              │  │
│  │  - CauseSelector        │  │  - AISuggestionCard     │  │
│  │  - QuestionCard        │  │  - 输入框               │  │
│  │  - AmountCalculator     │  │                         │  │
│  │  - EvidenceUploader    │  │  AIContextBridge        │  │
│  │  - DocumentPreview     │  │  - 步骤状态订阅          │  │
│  │                         │  │  - 上下文同步            │  │
│  └─────────────────────────┘  │  - 建议回写              │  │
│              ▲                └─────────────────────────┘  │
│              │                          ▲                  │
│              │  step_complete 事件        │                  │
│              └──────────────────────────┘                  │
│                                                          │
│              AI Context Store (Zustand)                   │
│    - currentStep, stepData, caseSummary, aiMessages      │
└─────────────────────────────────────────────────────────┘
```

### 组件职责

| 组件 | 职责 |
|------|------|
| `AIContextBridge` | 管理 AI 上下文状态，订阅向导状态变化，在步骤完成时组装上下文并触发 AI 分析 |
| `AISuggestionCard` | 渲染 AI 返回的可操作建议卡片（确认/忽略按钮） |
| `useAIContext` | Hook：连接向导状态 ↔ AI 上下文，管理上下文同步 |
| `useAISuggestion` | Hook：处理 AI 建议的确认/忽略逻辑，将确认的建议值写入 caseStore |
| 改造 `AIChatPanel` | 新增建议卡片渲染 + 对话式展示 + 主动分析触发 |
| 改造 `caseStore` | 新增 `stepData`、`caseSummary`、`aiMessages` 字段 |

---

## 三、数据流设计

### 3.1 上下文同步时机

**只在步骤完成时同步**（点击"下一步"时），而非每个字段变化时同步。

```
用户点击"下一步"
       │
       ▼
AIContextBridge 收集上下文：
  - currentStep（当前步骤）
  - stepData[currentStep]（当前步骤填写的数据）
  - 前置步骤摘要（previousStepsSummary，对应 evidence_status 等）
  - 证据状态（evidenceStatus，对应 has_labor_contract 等布尔标志）
  - 已判定的案由（causeCodes）
       │
       ▼
POST /api/ai/contextual-analysis
       │
       ▼
AI 返回：
  - analysis（string）：对话式分析文本
  - suggestions（array）：建议列表
       │
       ▼
更新 caseStore.aiMessages
更新 caseStore.pendingSuggestions
       │
       ▼
AIChatPanel 渲染：
  - 对话消息（analysis 文本）
  - 建议卡片（suggestions 列表）
```

### 3.2 建议卡片数据结构

```typescript
interface AISuggestion {
  id: string                    // 唯一 ID
  type: 'field_correction' | 'missing_info' | 'risk_alert' | 'calculation'
  field: string                // 对应表单字段路径，如 "q3" 或 "estimated_amount"
  fieldLabel: string           // 字段中文标签，如 "拖欠工资金额"
  suggestedValue: any          // 建议值
  confidence: number           // 0-1 置信度
  reason: string               // 中文解释
}
```

### 3.3 置信度策略

| 置信度 | 行为 |
|--------|------|
| ≥ 0.9 | 显示建议卡片，用户可直接确认 |
| 0.7 - 0.9 | 显示建议卡片，带"AI参考"标签 |
| < 0.7 | 仅在对话中文字描述，不生成可操作卡片 |

---

## 四、AI 对话上下文结构

### 4.1 context_data 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| case_summary | string | 案件事实摘要，基于前置步骤的答案生成 |
| answers_this_step | object | 当前步骤用户填写的问答对，key 为 question_id |
| previous_steps_summary | object | 前置步骤的摘要，key 为步骤编号 |
| evidence_status | object | 证据状态，包含 total（总数）及各类型布尔标志 |
| user_question | string \| null | 用户主动提问的内容，无提问时为 null |

**字段详情：**

- `evidence_status` 结构固定为：
  ```json
  {
    "total": 2,
    "has_labor_contract": true,
    "has_salary_record": false,
    "has_termination_proof": false
  }
  ```
  各布尔标志表示该类证据是否已上传/可补充。

- `previous_steps_summary` 结构示例：
  ```json
  {
    "step1": { "mode": "AI问答", "selected_cause": "欠薪" },
    "step2": { "cause_type": "未支付工资", "amount_claimed": null }
  }
  ```

### 4.2 响应格式

```json
{
  "analysis": "根据您提供的信息，您的案件属于拖欠工资纠纷。月薪8000元，拖欠3个月工资共计24000元。根据《劳动合同法》第38条，您有权解除劳动合同并主张经济补偿。\n\n另外，我注意到您的入职时间是2022年3月，到被辞退时工龄已满2年，经济补偿金应为1个月工资。",
  "suggestions": [
    {
      "id": "sug_001",
      "type": "calculation",
      "field": "q5_estimated_amount",
      "fieldLabel": "拖欠工资金额",
      "suggestedValue": 24000,
      "confidence": 0.95,
      "reason": "月薪8000元 × 3个月 = 24000元"
    },
    {
      "id": "sug_002",
      "type": "missing_info",
      "field": "q6_compensation",
      "fieldLabel": "经济补偿金",
      "suggestedValue": 8000,
      "confidence": 0.88,
      "reason": "工龄2年，应得1个月工资作为经济补偿"
    }
  ]
}
```

---

## 五、后端接口

### 5.1 新增接口

```
POST /api/ai/contextual-analysis
```

**请求体：**

| 字段 | 类型 | 说明 |
|------|------|------|
| case_id | UUID | 案件 ID（顶层字段） |
| current_step | int | 当前步骤 1-9（顶层字段） |
| context_data | object | 案件上下文，包含以下字段，详见下方示例 |

**context_data 结构示例：**

```json
{
  "case_id": "uuid-string",
  "current_step": 3,
  "step_label": "信息补全",
  "case_summary": "用户反映公司拖欠2024年1-3月工资，月薪8000元，已工作2年，因公司经营困难被口头辞退。",
  "answers_this_step": {
    "q1": "拖欠工资",
    "q2": "2022年3月1日入职",
    "q3": "8000元/月",
    "q4": "2024年3月15日被辞退"
  },
  "previous_steps_summary": {
    "step1": { "mode": "AI问答", "selected_cause": "欠薪" },
    "step2": { "cause_type": "未支付工资", "amount_claimed": null }
  },
  "evidence_status": {
    "total": 2,
    "has_labor_contract": true,
    "has_salary_record": false,
    "has_termination_proof": false
  },
  "user_question": null
}
```

> **结构说明：** `case_id` 和 `current_step` 为顶层字段，其余上下文信息均在 `context_data` 对象内。API 收到请求后，将顶层字段与 `context_data` 合并后一同处理。

### 5.2 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| analysis | string | AI 对话式分析文本 |
| suggestions | array | 建议列表，结构见 3.2 |

### 5.3 现有接口兼容

现有 `/api/ai/review` 等接口保持不变。

---

## 六、UI 布局

```
┌──────────────────────────────────────────────────────────────┐
│  Step 1  →  Step 2  →  Step 3  →  ...  →  Step 9          │
│  模式选择    问题初判   信息补全          求助复核             │
├─────────────────────────────────┬────────────────────────────┤
│                                 │  🤖 AI 助手                 │
│   步骤内容区域                    │  ────────────────────────  │
│                                 │                            │
│   QuestionCard                 │  [系统]: 根据您已完成的信息， │
│   AmountCalculator             │  发现以下可优化项：            │
│   EvidenceUploader             │                            │
│                                 │  ┌──────────────────────┐   │
│                                 │  │ 💡 金额修正           │   │
│                                 │  │ 拖欠工资: 24,000元    │   │
│                                 │  │ [确认] [忽略]         │   │
│                                 │  └──────────────────────┘   │
│                                 │                            │
│   [上一步]  [下一步 →]           │  ┌──────────────────────┐   │
│                                 │  │ 💡 补充信息            │   │
│                                 │  │ 缺少：银行工资流水      │   │
│                                 │  │ [查看收集方法]         │   │
│                                 │  └──────────────────────┘   │
│                                 │                            │
│                                 │  ────────────────────────  │
│                                 │  [输入您的问题...] [发送]    │
└─────────────────────────────────┴────────────────────────────┘
```

- 侧边栏固定宽度 **320px**
- 左侧内容区域 **自适应**
- 侧边栏始终可见，不折叠

---

## 七、文件变更清单

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `frontend/src/stores/aiContextStore.ts` | AI 上下文状态管理（Zustand） |
| `frontend/src/components/ai/AISuggestionCard.tsx` | AI 建议卡片组件 |
| `frontend/src/components/ai/AIContextBridge.tsx` | AI 上下文桥接组件 |
| `frontend/src/hooks/useAIContext.ts` | AI 上下文 Hook |
| `frontend/src/hooks/useAISuggestion.ts` | AI 建议处理 Hook |
| `frontend/src/services/aiService.ts` (改造) | 新增 contextualAnalysis 方法 |
| `backend/app/api/ai.py` (改造) | 新增 `/api/ai/contextual-analysis` 端点 |
| `backend/app/agents/contextual_agent.py` | 新增上下文分析 Agent |

### 改造文件

| 文件路径 | 改造内容 |
|----------|---------|
| `frontend/src/components/ai/AIChatPanel.tsx` | 渲染建议卡片，响应主动分析 |
| `frontend/src/stores/caseStore.ts` | 新增 stepData、caseSummary、aiMessages 字段 |
| `frontend/src/pages/CaseWizard.tsx` | 集成 AIContextBridge |
| `frontend/src/components/layout/StepContent.tsx` | 步骤完成时触发上下文同步 |
| `frontend/src/App.tsx` | 侧边栏布局改造 |
| `frontend/src/App.css` | 侧边栏样式 |
| `frontend/src/services/api.ts` | 新增 contextualAnalysis API |

---

## 八、实现顺序

### Phase 1: 状态管理基础
1. 改造 `caseStore` 新增字段
2. 新建 `aiContextStore`
3. 新建 `AIContextBridge` 组件

### Phase 2: 后端接口
4. 新增 `/api/ai/contextual-analysis` 端点
5. 新建 `contextual_agent.py`

### Phase 3: 前端 UI
6. 新建 `AISuggestionCard` 组件
7. 改造 `AIChatPanel` 渲染建议卡片
8. 改造布局为左右分栏

### Phase 4: 联动逻辑
9. 实现 `useAIContext` 上下文同步
10. 实现 `useAISuggestion` 确认/忽略逻辑
11. 步骤完成触发 AI 分析流程

---

## 九、测试要点

| 测试场景 | 预期行为 |
|----------|---------|
| 完成 Step 2 后 | 侧边栏自动显示 AI 分析和建议卡片 |
| 点击建议卡片"确认" | 对应表单字段高亮显示预填值 |
| 点击建议卡片"忽略" | 卡片消失，不影响表单 |
| 在 Step 3 输入数据后点击"下一步" | AI 上下文包含 Step 2 + Step 3 数据 |
| 用户主动发送消息 | AI 上下文包含用户消息，AI 响应追加到对话 |

---

*文档版本: v1.0*
*生成日期: 2026-04-14*
