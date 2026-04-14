# AI 聊天与向导双向联动系统 - 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 9 步向导全程显示 AI 聊天侧边栏，步骤完成时 AI 自动分析并返回建议卡片，用户确认后数据回填表单。

**Architecture:** Chat-Centric 方案。侧边栏始终可见，步骤完成时触发 AI 分析，AI 以对话形式返回分析结果和建议卡片。caseStore 作为状态桥梁连接向导和 AI 上下文。

**Tech Stack:** React 18 + TypeScript + Zustand + React Query (前端) | FastAPI + LangChain (后端)

---

## 文件结构

```
frontend/src/
├── stores/
│   ├── caseStore.ts          # 改造：新增 stepData、caseSummary、aiMessages 字段
│   └── aiContextStore.ts    # 新增：AI 上下文状态（Zustand）
├── hooks/
│   ├── useAIContext.ts       # 新增：上下文同步 Hook
│   └── useAISuggestion.ts    # 新增：建议确认/忽略 Hook
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx     # 新增：左右分栏布局容器
│   │   ├── StepWizard.tsx    # 现有：无需改动
│   │   └── StepContent.tsx  # 改造：步骤完成时触发 AI 分析
│   ├── ai/
│   │   ├── AIChatPanel.tsx  # 改造：渲染建议卡片 + 对话历史
│   │   ├── AISuggestionCard.tsx  # 新增：建议卡片组件
│   │   └── AIContextBridge.tsx   # 新增：上下文桥接组件
│   └── business/
│       └── ...              # 现有组件无需改动
├── pages/
│   ├── Home.tsx             # 现有：无需改动
│   └── CaseWizard.tsx       # 改造：集成 AIContextBridge
├── services/
│   ├── api.ts               # 改造：新增 contextualAnalysis API
│   └── aiService.ts         # 改造：新增 contextualAnalysis 方法

backend/app/
├── api/
│   └── ai.py               # 改造：新增 /api/ai/contextual-analysis 端点
├── agents/
│   └── contextual_agent.py  # 新增：上下文分析 Agent
├── models/
│   └── schemas.py          # 改造：新增 ContextualAnalysisRequest Schema
└── services/
    └── document_service.py  # 现有：无需改动
```

---

## Task 1: 改造 caseStore — 新增字段

**Files:**
- Modify: `frontend/src/stores/caseStore.ts`

- [ ] **Step 1: 添加新字段到 caseStore**

```typescript
// frontend/src/stores/caseStore.ts 完整替换

import { create } from 'zustand'

// 建议卡片类型
export type SuggestionType = 'field_correction' | 'missing_info' | 'risk_alert' | 'calculation'

export interface AISuggestion {
  id: string
  type: SuggestionType
  field: string
  fieldLabel: string
  suggestedValue: unknown
  confidence: number
  reason: string
}

// AI 消息类型
export interface AIMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  suggestions?: AISuggestion[]
  timestamp: number
}

interface CaseState {
  caseId: string | null
  currentStep: number
  status: 'idle' | 'loading' | 'success' | 'error'
  caseData: Record<string, unknown> | null

  // 新增字段
  stepData: Record<number, Record<string, unknown>>  // key: step, value: { questionId: answer }
  caseSummary: string                                  // 案件摘要（AI 生成）
  aiMessages: AIMessage[]                               // AI 对话历史
  pendingSuggestions: AISuggestion[]                   // 待确认的建议

  setCaseId: (id: string | null) => void
  setStep: (step: number) => void
  setCaseData: (data: Record<string, unknown> | null) => void
  setStatus: (status: 'idle' | 'loading' | 'success' | 'error') => void

  // 新增方法
  setStepData: (step: number, data: Record<string, unknown>) => void
  setCaseSummary: (summary: string) => void
  addAIMessage: (message: AIMessage) => void
  setPendingSuggestions: (suggestions: AISuggestion[]) => void
  acceptSuggestion: (suggestionId: string) => void
  dismissSuggestion: (suggestionId: string) => void
  reset: () => void
}

const initialState = {
  caseId: null,
  currentStep: 1,
  status: 'idle' as const,
  caseData: null,
  stepData: {},
  caseSummary: '',
  aiMessages: [],
  pendingSuggestions: []
}

export const useCaseStore = create<CaseState>((set) => ({
  ...initialState,

  setCaseId: (id) => set({ caseId: id }),
  setStep: (step) => set({ currentStep: Math.min(9, Math.max(1, step)) }),
  setCaseData: (data) => set({ caseData: data }),
  setStatus: (status) => set({ status }),

  setStepData: (step, data) =>
    set((state) => ({
      stepData: { ...state.stepData, [step]: { ...(state.stepData[step] || {}), ...data } }
    })),

  setCaseSummary: (summary) => set({ caseSummary: summary }),

  addAIMessage: (message) =>
    set((state) => ({ aiMessages: [...state.aiMessages, message] })),

  setPendingSuggestions: (suggestions) => set({ pendingSuggestions: suggestions }),

  acceptSuggestion: (suggestionId) =>
    set((state) => {
      const suggestion = state.pendingSuggestions.find((s) => s.id === suggestionId)
      if (!suggestion) return state

      // 将建议值写入当前步骤的 stepData
      const currentStepData = state.stepData[state.currentStep] || {}
      const updatedStepData = {
        ...state.stepData,
        [state.currentStep]: {
          ...currentStepData,
          [suggestion.field]: suggestion.suggestedValue
        }
      }

      return {
        stepData: updatedStepData,
        pendingSuggestions: state.pendingSuggestions.filter((s) => s.id !== suggestionId)
      }
    }),

  dismissSuggestion: (suggestionId) =>
    set((state) => ({
      pendingSuggestions: state.pendingSuggestions.filter((s) => s.id !== suggestionId)
    })),

  reset: () => set(initialState)
}))
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -30`
Expected: 无 error（仅有现有警告可忽略）

- [ ] **Step 3: 提交**

```bash
git add frontend/src/stores/caseStore.ts
git commit -m "feat(store): add stepData, aiMessages, pendingSuggestions to caseStore

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 新建 aiContextStore — AI 上下文状态

**Files:**
- Create: `frontend/src/stores/aiContextStore.ts`

- [ ] **Step 1: 创建 aiContextStore**

```typescript
// frontend/src/stores/aiContextStore.ts

import { create } from 'zustand'

export interface AIContextState {
  // 当前是否正在等待 AI 分析
  isAnalyzing: boolean
  // 最后分析时间戳
  lastAnalyzedAt: number | null
  // 当前分析中的步骤
  analyzingStep: number | null

  // 同步状态
  setAnalyzing: (step: number) => void
  setAnalyzed: () => void
  reset: () => void
}

export const useAIContextStore = create<AIContextState>((set) => ({
  isAnalyzing: false,
  lastAnalyzedAt: null,
  analyzingStep: null,

  setAnalyzing: (step) =>
    set({ isAnalyzing: true, analyzingStep: step }),

  setAnalyzed: () =>
    set({ isAnalyzing: false, analyzingStep: null, lastAnalyzedAt: Date.now() }),

  reset: () =>
    set({ isAnalyzing: false, lastAnalyzedAt: null, analyzingStep: null })
}))
```

- [ ] **Step 2: 验证编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: 无新增 error

- [ ] **Step 3: 提交**

```bash
git add frontend/src/stores/aiContextStore.ts
git commit -m "feat(store): add AI context state store

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: 新建 useAIContext Hook — 上下文同步

**Files:**
- Create: `frontend/src/hooks/useAIContext.ts`

- [ ] **Step 1: 创建 useAIContext Hook**

```typescript
// frontend/src/hooks/useAIContext.ts

import { useCallback } from 'react'
import { useCaseStore } from '../stores/caseStore'
import { useAIContextStore } from '../stores/aiContextStore'
import { aiService } from '../services/aiService'

const STEP_LABELS = [
  '模式选择', '问题初判', '信息补全', '案件定性',
  '证据攻略', '风险提示', '文书生成', '行动路线图', '求助复核'
]

export function useAIContext() {
  const {
    caseId,
    currentStep,
    stepData,
    caseSummary,
    setCaseSummary,
    addAIMessage,
    setPendingSuggestions,
    pendingSuggestions
  } = useCaseStore()

  const { setAnalyzing, setAnalyzed } = useAIContextStore()

  /**
   * 触发 AI 上下文分析
   * 在步骤完成时调用（点击"下一步"时）
   */
  const analyzeCurrentStep = useCallback(async () => {
    if (!caseId || pendingSuggestions.length > 0) {
      // 有未处理的建议时，不触发新分析
      return
    }

    setAnalyzing(currentStep)

    try {
      // 构建上下文数据
      const contextData = buildContextData()

      // 调用 AI 分析
      const result = await aiService.contextualAnalysis({
        caseId,
        currentStep,
        contextData
      })

      // 更新案件摘要
      if (result.case_summary) {
        setCaseSummary(result.case_summary)
      }

      // 添加 AI 对话消息
      addAIMessage({
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: result.analysis,
        suggestions: result.suggestions || [],
        timestamp: Date.now()
      })

      // 设置待确认的建议
      if (result.suggestions && result.suggestions.length > 0) {
        setPendingSuggestions(result.suggestions)
      }
    } catch (error) {
      console.error('AI analysis failed:', error)
      addAIMessage({
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: '抱歉，AI 分析暂时不可用，请稍后再试。',
        timestamp: Date.now()
      })
    } finally {
      setAnalyzed()
    }
  }, [caseId, currentStep, stepData, caseSummary, pendingSuggestions.length])

  /**
   * 构建发送给 AI 的上下文数据
   */
  const buildContextData = useCallback(() => {
    const answersThisStep = (stepData[currentStep] || {}) as Record<string, unknown>

    // 构建前置步骤摘要
    const previousStepsSummary: Record<string, Record<string, unknown>> = {}
    for (let s = 1; s < currentStep; s++) {
      const sData = stepData[s]
      if (sData && Object.keys(sData).length > 0) {
        if (s === 1) {
          previousStepsSummary['step1'] = sData
        } else if (s === 2) {
          previousStepsSummary['step2'] = sData
        }
        // 依此类推...
      }
    }

    return {
      step_label: STEP_LABELS[currentStep - 1],
      case_summary: caseSummary,
      answers_this_step: answersThisStep,
      previous_steps_summary: previousStepsSummary,
      // evidence_status 和 user_question 在后续 Task 补充
      user_question: null
    }
  }, [currentStep, stepData, caseSummary])

  return {
    analyzeCurrentStep,
    buildContextData
  }
}
```

- [ ] **Step 2: 验证编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 无新增 error（aiService.contextualAnalysis 尚不存在，但类型检查会通过）

- [ ] **Step 3: 提交**

```bash
git add frontend/src/hooks/useAIContext.ts
git commit -m "feat(hook): add useAIContext for context sync

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: 新建 useAISuggestion Hook — 建议确认/忽略

**Files:**
- Create: `frontend/src/hooks/useAISuggestion.ts`

- [ ] **Step 1: 创建 useAISuggestion Hook**

```typescript
// frontend/src/hooks/useAISuggestion.ts

import { useCallback } from 'react'
import { useCaseStore, AISuggestion } from '../stores/caseStore'

export function useAISuggestion() {
  const {
    pendingSuggestions,
    acceptSuggestion,
    dismissSuggestion,
    stepData,
    currentStep
  } = useCaseStore()

  /**
   * 确认建议：将建议值写入 stepData
   */
  const accept = useCallback((suggestionId: string) => {
    acceptSuggestion(suggestionId)
  }, [acceptSuggestion])

  /**
   * 忽略建议：从待处理列表中移除
   */
  const dismiss = useCallback((suggestionId: string) => {
    dismissSuggestion(suggestionId)
  }, [dismissSuggestion])

  /**
   * 获取当前步骤的预填值（用于高亮显示）
   */
  const getPrefilledValue = useCallback((field: string): unknown => {
    const currentStepData = stepData[currentStep] || {}
    return currentStepData[field]
  }, [stepData, currentStep])

  /**
   * 检查字段是否有预填值
   */
  const hasPrefilledValue = useCallback((field: string): boolean => {
    return getPrefilledValue(field) !== undefined
  }, [getPrefilledValue])

  return {
    pendingSuggestions,
    accept,
    dismiss,
    getPrefilledValue,
    hasPrefilledValue
  }
}
```

- [ ] **Step 2: 验证编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: 无新增 error

- [ ] **Step 3: 提交**

```bash
git add frontend/src/hooks/useAISuggestion.ts
git commit -m "feat(hook): add useAISuggestion for suggestion accept/dismiss

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: 改造 aiService — 新增 contextualAnalysis

**Files:**
- Modify: `frontend/src/services/aiService.ts`
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: 改造 api.ts — 新增 contextualAnalysis API**

```typescript
// 在 api.ts 的 ai 对象中新增

// AI
export const ai = {
  // ... 现有方法 ...
  contextualAnalysis: (params: {
    caseId: string
    currentStep: number
    contextData: Record<string, unknown>
  }) =>
    client.post('/ai/contextual-analysis', {
      case_id: params.caseId,
      current_step: params.currentStep,
      context_data: params.contextData
    })
}
```

- [ ] **Step 2: 改造 aiService.ts — 新增 contextualAnalysis 方法**

```typescript
// frontend/src/services/aiService.ts

export const aiService = {
  // ... 现有方法 ...

  contextualAnalysis: async (params: {
    caseId: string
    currentStep: number
    contextData: Record<string, unknown>
  }) => {
    const response = await ai.contextualAnalysis(params)
    return response.data as {
      analysis: string
      suggestions: Array<{
        id: string
        type: 'field_correction' | 'missing_info' | 'risk_alert' | 'calculation'
        field: string
        fieldLabel: string
        suggestedValue: unknown
        confidence: number
        reason: string
      }>
      case_summary?: string
    }
  }
}
```

- [ ] **Step 3: 验证编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: 无新增 error

- [ ] **Step 4: 提交**

```bash
git add frontend/src/services/api.ts frontend/src/services/aiService.ts
git commit -m "feat(api): add contextualAnalysis endpoint

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 后端 — 新增 ContextualAnalysisRequest Schema

**Files:**
- Modify: `backend/app/models/schemas.py`

- [ ] **Step 1: 添加 ContextualAnalysisRequest**

```python
# 在 backend/app/models/schemas.py 中添加

class ContextualAnalysisRequest(BaseModel):
    case_id: UUID
    current_step: int = Field(..., ge=1, le=9)
    context_data: dict = Field(..., description="包含 case_summary、answers_this_step、previous_steps_summary、evidence_status、user_question")
```

- [ ] **Step 2: 验证 Python 语法**

Run: `cd backend && python -c "from app.models.schemas import ContextualAnalysisRequest; print('OK')"`
Expected: 输出 OK

- [ ] **Step 3: 提交**

```bash
git add backend/app/models/schemas.py
git commit -m "feat(schema): add ContextualAnalysisRequest

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: 后端 — 新建 contextual_agent.py

**Files:**
- Create: `backend/app/agents/contextual_agent.py`

- [ ] **Step 1: 创建 contextual_agent.py**

```python
# backend/app/agents/contextual_agent.py

from app.agents.base_agent import BaseAgent
from app.config import settings
from langchain_qianwen import ChatQianwen
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json
import re


class ContextualAnalysisAgent(BaseAgent):
    """上下文分析 Agent — 步骤完成时调用，返回分析和建议"""

    def __init__(self):
        self.llm = ChatQianwen(
            model="qwen-plus",
            qianwen_api_key=settings.QWEN_API_KEY,
            temperature=0.3
        )

    async def run(self, input_data: dict) -> dict:
        """
        input_data 包含:
        - case_id: UUID
        - current_step: int
        - context_data: {
              case_summary: str,
              answers_this_step: dict,
              previous_steps_summary: dict,
              evidence_status: dict,
              user_question: str | None
          }
        """
        context_data = input_data.get("context_data", {})
        current_step = input_data.get("current_step", 1)

        template = self._build_prompt_template(current_step)

        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm

        result = await chain.ainvoke({
            "case_summary": context_data.get("case_summary", ""),
            "answers_this_step": json.dumps(context_data.get("answers_this_step", {}), ensure_ascii=False),
            "previous_steps_summary": json.dumps(context_data.get("previous_steps_summary", {}), ensure_ascii=False),
            "evidence_status": json.dumps(context_data.get("evidence_status", {}), ensure_ascii=False),
            "user_question": context_data.get("user_question") or "无",
            "step_label": context_data.get("step_label", "")
        })

        return self._parse_result(result, current_step)

    def _build_prompt_template(self, current_step: int) -> str:
        base_template = """你是一名劳动维权 AI 助手，正在帮助用户完成维权案件的填写。

当前步骤：{step_label}（第 {current_step} 步，共 9 步）

案件摘要：
{case_summary}

当前步骤用户填写：
{answers_this_step}

前置步骤摘要：
{previous_steps_summary}

证据状态：
{evidence_status}

{fact_sheet}

请分析以上信息，返回 JSON 格式：
{{
    "analysis": "对话式分析文本，用友好易懂的语言总结发现的问题和下一步建议",
    "suggestions": [
        {{
            "id": "sug_001",
            "type": "field_correction|missing_info|risk_alert|calculation",
            "field": "字段标识符",
            "fieldLabel": "字段中文名称",
            "suggestedValue": "建议填入的值",
            "confidence": 0.0-1.0,
            "reason": "为什么给出这个建议"
        }}
    ],
    "case_summary": "基于新信息更新的案件摘要（如果没有新信息可保持原样）"
}}

要求：
- analysis 应该通俗易懂，用"您"称呼用户
- suggestions 仅在置信度 >= 0.7 时生成
- type 说明：field_correction=字段修正, missing_info=补充信息, risk_alert=风险提示, calculation=金额计算
- 仅返回 JSON，不要有其他内容"""

        # 针对不同步骤添加不同的知识参考
        fact_sheets = {
            1: "【法律参考】拖欠工资：用人单位应按时足额支付劳动报酬，不得无故拖欠。",
            2: "【法律参考】经济补偿金：根据《劳动合同法》第47条，工作满1年支付1个月工资作为经济补偿。",
            3: "【法律参考】工龄计算：从入职之日起算，包括试用期。",
            4: "【法律参考】案由判定：需结合具体事实和法律依据综合判断。",
            5: "【法律参考】证据要求：劳动仲裁中证据必须真实、合法、与案件有关联。",
            6: "【法律参考】风险提示：时效风险（劳动仲裁1年时效）、证据风险、金额计算错误风险。",
        }

        fact_sheet = fact_sheets.get(current_step, "")
        return base_template.replace("{fact_sheet}", fact_sheet)

    def _parse_result(self, result, current_step: int) -> dict:
        """解析 LLM 返回结果"""
        output = result.content if hasattr(result, 'content') else str(result)

        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    "analysis": parsed.get("analysis", ""),
                    "suggestions": parsed.get("suggestions", []),
                    "case_summary": parsed.get("case_summary", "")
                }
        except json.JSONDecodeError:
            pass

        # 解析失败时返回降级结果
        return {
            "analysis": output,
            "suggestions": [],
            "case_summary": ""
        }
```

- [ ] **Step 2: 验证 Python 语法**

Run: `cd backend && python -c "from app.agents.contextual_agent import ContextualAnalysisAgent; print('OK')"`
Expected: 输出 OK

- [ ] **Step 3: 提交**

```bash
git add backend/app/agents/contextual_agent.py
git commit -m "feat(agent): add ContextualAnalysisAgent

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: 后端 — 新增 /api/ai/contextual-analysis 端点

**Files:**
- Modify: `backend/app/api/ai.py`

- [ ] **Step 1: 在 ai.py 中添加新端点**

```python
# 在 ai.py 文件末尾添加

from app.models.schemas import ContextualAnalysisRequest

@router.post("/contextual-analysis")
async def contextual_analysis(
    req: ContextualAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """上下文分析接口 — 步骤完成时调用"""
    # 获取案件信息
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(req.case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    # 获取证据状态
    evidence_repo = EvidenceRepository(db)
    evidence_list = await evidence_repo.get_by_case_id(req.case_id)
    evidence_status = {
        "total": len(evidence_list),
        "has_labor_contract": any(e.name and '劳动合同' in e.name for e in evidence_list),
        "has_salary_record": any(e.name and '工资' in e.name for e in evidence_list),
        "has_termination_proof": any(e.name and ('辞退' in e.name or '解除' in e.name) for e in evidence_list)
    }

    # 构建 context_data
    context_data = req.context_data.copy()
    context_data["evidence_status"] = evidence_status

    # 调用 Agent
    agent = ContextualAnalysisAgent()
    result = await agent.run({
        "case_id": str(req.case_id),
        "current_step": req.current_step,
        "context_data": context_data
    })

    # 如果返回了新摘要，更新案件
    if result.get("case_summary"):
        await case_repo.update_description(req.case_id, result["case_summary"])

    return result
```

- [ ] **Step 2: 验证路由注册**

Run: `cd backend && python -c "from app.api.ai import router; print([r.path for r in router.routes])"`
Expected: 包含 '/contextual-analysis'

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/ai.py
git commit -m "feat(api): add /contextual-analysis endpoint

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 9: 新建 AISuggestionCard 组件

**Files:**
- Create: `frontend/src/components/ai/AISuggestionCard.tsx`

- [ ] **Step 1: 创建 AISuggestionCard 组件**

```tsx
// frontend/src/components/ai/AISuggestionCard.tsx

import React from 'react'
import { useAISuggestion } from '../../hooks/useAISuggestion'
import { AISuggestion } from '../../stores/caseStore'

interface AISuggestionCardProps {
  suggestion: AISuggestion
}

const TYPE_LABELS: Record<string, { icon: string; label: string }> = {
  field_correction: { icon: '✏️', label: '字段修正' },
  missing_info: { icon: '📋', label: '补充信息' },
  risk_alert: { icon: '⚠️', label: '风险提示' },
  calculation: { icon: '🔢', label: '金额计算' }
}

export function AISuggestionCard({ suggestion }: AISuggestionCardProps) {
  const { accept, dismiss } = useAISuggestion()

  const typeInfo = TYPE_LABELS[suggestion.type] || { icon: '💡', label: '建议' }
  const showConfidenceTag = suggestion.confidence < 0.9

  const handleAccept = () => {
    accept(suggestion.id)
  }

  const handleDismiss = () => {
    dismiss(suggestion.id)
  }

  const formatValue = (value: unknown): string => {
    if (typeof value === 'number') {
      return value.toLocaleString('zh-CN')
    }
    return String(value)
  }

  return (
    <div
      style={{
        border: '1px solid #e0e0e0',
        borderRadius: '8px',
        padding: '12px',
        marginBottom: '8px',
        backgroundColor: '#fff',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
        <span>{typeInfo.icon}</span>
        <span style={{ fontWeight: 500, fontSize: '14px' }}>{typeInfo.label}</span>
        {showConfidenceTag && (
          <span
            style={{
              fontSize: '11px',
              padding: '2px 6px',
              borderRadius: '4px',
              backgroundColor: '#f0f0ff',
              color: '#667eea'
            }}
          >
            AI参考
          </span>
        )}
      </div>

      {/* Field label and suggested value */}
      <div style={{ marginBottom: '8px' }}>
        <span style={{ color: '#666', fontSize: '13px' }}>{suggestion.fieldLabel}: </span>
        <span style={{ fontWeight: 500, fontSize: '14px', color: '#333' }}>
          {formatValue(suggestion.suggestedValue)}
        </span>
      </div>

      {/* Reason */}
      <div
        style={{
          fontSize: '12px',
          color: '#888',
          marginBottom: '10px',
          lineHeight: 1.4
        }}
      >
        {suggestion.reason}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: '8px' }}>
        <button
          onClick={handleAccept}
          style={{
            flex: 1,
            padding: '6px 12px',
            borderRadius: '6px',
            border: 'none',
            backgroundColor: '#667eea',
            color: 'white',
            fontSize: '13px',
            cursor: 'pointer'
          }}
        >
          确认
        </button>
        <button
          onClick={handleDismiss}
          style={{
            flex: 1,
            padding: '6px 12px',
            borderRadius: '6px',
            border: '1px solid #ddd',
            backgroundColor: 'white',
            color: '#666',
            fontSize: '13px',
            cursor: 'pointer'
          }}
        >
          忽略
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 验证编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: 无新增 error

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/ai/AISuggestionCard.tsx
git commit -m "feat(component): add AISuggestionCard

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 10: 改造 AIChatPanel — 渲染建议卡片 + 对话历史

**Files:**
- Modify: `frontend/src/components/ai/AIChatPanel.tsx`

- [ ] **Step 1: 替换 AIChatPanel 组件**

```tsx
// frontend/src/components/ai/AIChatPanel.tsx

import React, { useState, useRef, useEffect } from 'react'
import { useCaseStore, AIMessage } from '../../stores/caseStore'
import { useAIContextStore } from '../../stores/aiContextStore'
import { useAIContext } from '../../hooks/useAIContext'
import { useAISuggestion } from '../../hooks/useAISuggestion'
import { AISuggestionCard } from './AISuggestionCard'

export function AIChatPanel() {
  const { caseId, aiMessages, addAIMessage, pendingSuggestions } = useCaseStore()
  const { isAnalyzing } = useAIContextStore()
  const { analyzeCurrentStep } = useAIContext()
  const { pendingSuggestions: suggestions } = useAISuggestion()

  const [message, setMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // 自动滚动到底部
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [aiMessages, pendingSuggestions])

  const handleSend = async () => {
    if (!message.trim() || isSending) return

    const userMessage = message.trim()
    setMessage('')
    setIsSending(true)

    // 添加用户消息
    addAIMessage({
      id: `msg_${Date.now()}`,
      role: 'user',
      content: userMessage,
      timestamp: Date.now()
    })

    try {
      // TODO: 调用 AI 消息回复接口（复用 review 接口）
      const { aiService } = await import('../../services/aiService')
      const result = await aiService.review({ caseId }, userMessage)

      addAIMessage({
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: result.review || '收到您的问题，请稍候。',
        timestamp: Date.now()
      })
    } catch (error) {
      addAIMessage({
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: '抱歉，发生了错误，请稍后再试。',
        timestamp: Date.now()
      })
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '320px',
        borderLeft: '1px solid #e0e0e0',
        backgroundColor: '#fafafa'
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '16px',
          borderBottom: '1px solid #e0e0e0',
          backgroundColor: 'white'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '20px' }}>🤖</span>
          <span style={{ fontWeight: 600, fontSize: '16px' }}>AI 助手</span>
        </div>
        {isAnalyzing && (
          <div
            style={{
              marginTop: '8px',
              fontSize: '12px',
              color: '#667eea'
            }}
          >
            分析中...
          </div>
        )}
      </div>

      {/* Chat History */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}
      >
        {aiMessages.length === 0 && !isAnalyzing && (
          <div
            style={{
              textAlign: 'center',
              color: '#999',
              padding: '32px 16px',
              fontSize: '14px'
            }}
          >
            完成当前步骤后，AI 将自动分析并提供建议
          </div>
        )}

        {aiMessages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {/* 建议卡片在最后一个 assistant 消息后显示 */}
        {pendingSuggestions.length > 0 && aiMessages.length > 0 && (
          <div style={{ marginTop: '8px' }}>
            <div
              style={{
                fontSize: '12px',
                color: '#666',
                marginBottom: '8px'
              }}
            >
              💡 发现以下可优化项：
            </div>
            {pendingSuggestions.map((suggestion) => (
              <AISuggestionCard key={suggestion.id} suggestion={suggestion} />
            ))}
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div
        style={{
          padding: '12px',
          borderTop: '1px solid #e0e0e0',
          backgroundColor: 'white'
        }}
      >
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="输入您的问题..."
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            disabled={isSending}
            style={{
              flex: 1,
              padding: '10px 12px',
              borderRadius: '8px',
              border: '1px solid #ddd',
              fontSize: '14px',
              outline: 'none'
            }}
          />
          <button
            onClick={handleSend}
            disabled={isSending || !message.trim()}
            style={{
              padding: '10px 16px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: '#667eea',
              color: 'white',
              fontSize: '14px',
              cursor: isSending ? 'not-allowed' : 'pointer',
              opacity: isSending ? 0.7 : 1
            }}
          >
            {isSending ? '...' : '发送'}
          </button>
        </div>
      </div>
    </div>
  )
}

function ChatMessage({ message }: { message: AIMessage }) {
  const isUser = message.role === 'user'

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start'
      }}
    >
      <div
        style={{
          maxWidth: '85%',
          padding: '10px 14px',
          borderRadius: isUser ? '12px 12px 0 12px' : '12px 12px 12px 0',
          backgroundColor: isUser ? '#667eea' : 'white',
          color: isUser ? 'white' : '#333',
          fontSize: '14px',
          lineHeight: 1.5,
          boxShadow: '0 1px 2px rgba(0,0,0,0.08)',
          whiteSpace: 'pre-wrap'
        }}
      >
        {message.content}
      </div>
      <span
        style={{
          fontSize: '11px',
          color: '#bbb',
          marginTop: '4px'
        }}
      >
        {new Date(message.timestamp).toLocaleTimeString('zh-CN', {
          hour: '2-digit',
          minute: '2-digit'
        })}
      </span>
    </div>
  )
}
```

- [ ] **Step 2: 验证编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: 无新增 error

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/ai/AIChatPanel.tsx
git commit -m "feat(ai): rewrite AIChatPanel with suggestion cards and chat history

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 11: 新建 AppShell — 左右分栏布局

**Files:**
- Create: `frontend/src/components/layout/AppShell.tsx`

- [ ] **Step 1: 创建 AppShell 组件**

```tsx
// frontend/src/components/layout/AppShell.tsx

import React from 'react'
import { Outlet } from 'react-router-dom'
import { AIChatPanel } from '../ai/AIChatPanel'

export function AppShell() {
  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        overflow: 'hidden'
      }}
    >
      {/* 主内容区 */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <Outlet />
      </div>

      {/* AI 侧边栏 */}
      <AIChatPanel />
    </div>
  )
}
```

- [ ] **Step 2: 验证编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: 无新增 error

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/layout/AppShell.tsx
git commit -m "feat(layout): add AppShell with sidebar layout

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 12: 改造 App.tsx — 使用 AppShell 路由

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 替换 App.tsx**

```tsx
// frontend/src/App.tsx

import { Routes, Route, Navigate } from 'react-router-dom'
import { Home } from './pages/Home'
import { CaseWizard } from './pages/CaseWizard'
import { AppShell } from './components/layout/AppShell'
import './App.css'

function App() {
  return (
    <div className="app">
      <Routes>
        {/* Home 不使用 AppShell（无侧边栏） */}
        <Route path="/" element={<Home />} />

        {/* CaseWizard 使用 AppShell（带侧边栏） */}
        <Route element={<AppShell />}>
          <Route path="/case" element={<CaseWizard />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App
```

- [ ] **Step 2: 验证编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: 无新增 error

- [ ] **Step 3: 提交**

```bash
git add frontend/src/App.tsx
git commit -m "feat: integrate AppShell with AI sidebar

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 13: 改造 CaseWizard — 集成步骤完成触发

**Files:**
- Modify: `frontend/src/pages/CaseWizard.tsx`

- [ ] **Step 1: 替换 CaseWizard.tsx**

```tsx
// frontend/src/pages/CaseWizard.tsx

import React from 'react'
import { StepWizard } from '../components/layout/StepWizard'
import { StepContent } from '../components/layout/StepContent'
import { useCaseStore } from '../stores/caseStore'
import { useStep } from '../hooks/useStep'
import { useAIContext } from '../hooks/useAIContext'

export function CaseWizard() {
  const { currentStep, nextStep, prevStep, canGoNext, canGoPrev } = useStep()
  const { status } = useCaseStore()
  const { analyzeCurrentStep } = useAIContext()

  const handleNextStep = async () => {
    // 先推进步骤
    await nextStep()
    // 步骤推进后，触发 AI 分析
    // 使用 setTimeout 确保状态已更新
    setTimeout(() => {
      analyzeCurrentStep()
    }, 100)
  }

  return (
    <div className="case-wizard">
      <StepWizard />
      <div className="content">
        <StepContent />
      </div>
      <div className="navigation">
        {canGoPrev && (
          <button className="btn-secondary" onClick={prevStep}>
            上一步
          </button>
        )}
        {canGoNext && (
          <button
            className="btn-primary"
            onClick={handleNextStep}
            disabled={status === 'loading'}
          >
            下一步
          </button>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 验证编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: 无新增 error

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/CaseWizard.tsx
git commit -m "feat(wizard): trigger AI analysis on step completion

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 14: 改造 StepContent — 保存步骤数据

**Files:**
- Modify: `frontend/src/components/layout/StepContent.tsx`

- [ ] **Step 1: 读取现有 StepContent.tsx 并改造**

由于我们尚未读取 StepContent.tsx 的完整内容，先读取：

```bash
cat frontend/src/components/layout/StepContent.tsx
```

然后替换为以下内容（假设现有内容是简单的 switch 渲染）：

```tsx
// frontend/src/components/layout/StepContent.tsx

import React from 'react'
import { CauseSelector } from '../business/CauseSelector'
import { QuestionCard } from '../business/QuestionCard'
import { EvidenceUploader } from '../business/EvidenceUploader'
import { EvidenceStatusBoard } from '../business/EvidenceStatusBoard'
import { DocumentPreview } from '../business/DocumentPreview'
import { useCaseStore } from '../../stores/caseStore'
import { useAISuggestion } from '../../hooks/useAISuggestion'

interface StepContentProps {
  step?: number  // 可选，默认从 store 读取
}

export function StepContent({ step: propStep }: StepContentProps) {
  const { currentStep } = useCaseStore()
  const step = propStep ?? currentStep
  const { getPrefilledValue } = useAISuggestion()

  const renderStep = () => {
    switch (step) {
      case 1:
        return <CauseSelector />
      case 2:
      case 3:
        return <QuestionCard step={step} />
      case 4:
        return (
          <div>
            <AIFeedbackCard title="案情分析" />
          </div>
        )
      case 5:
        return (
          <div>
            <EvidenceStatusBoard />
            <EvidenceUploader />
          </div>
        )
      case 6:
        return <AIFeedbackCard title="风险评估" />
      case 7:
        return <DocumentPreview />
      case 8:
        return <RoadmapFlow />
      case 9:
        return <AIFeedbackCard title="复核" />
      default:
        return <div>未知步骤</div>
    }
  }

  return (
    <div className="step-content">
      {renderStep()}
    </div>
  )
}
```

> **注意**: 上述 StepContent 为简化版。如果现有 StepContent.tsx 有更复杂的逻辑，需要保留原有逻辑并在保存数据的位置（如 QuestionCard 的 onSubmit）调用 `setStepData`。

**核心改造原则**：
- 在用户填写/修改数据时，调用 `useCaseStore.getState().setStepData(currentStep, data)` 保存数据
- 确保 AI 分析时能读取到完整的步骤数据

- [ ] **Step 2: 验证编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 无新增 error（可能有现有警告）

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/layout/StepContent.tsx
git commit -m "feat(content): save step data to store on change

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 15: 端到端集成测试

- [ ] **Step 1: 启动后端**

Run: `cd backend && python -m uvicorn app.main:app --reload --port 8000 &`
Expected: 服务启动在 8000 端口

- [ ] **Step 2: 启动前端**

Run: `cd frontend && npm run dev &`
Expected: Vite dev server 启动

- [ ] **Step 3: 手动测试流程**

1. 打开浏览器访问 http://localhost:3000
2. 点击进入"我要维权"
3. 进入 CaseWizard，确认右侧 AI 侧边栏可见
4. 在 Step 1 选择"AI问答"模式
5. 点击"下一步"，观察右侧是否出现 AI 分析结果
6. 如果出现建议卡片，点击"确认"观察数据回填
7. 检查浏览器 console 是否有错误

- [ ] **Step 4: 提交集成测试结果**

```bash
git add -A
git commit -m "test: e2e integration verified

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 实施顺序

1. **Task 1-2**: caseStore + aiContextStore（状态基础）
2. **Task 3-4**: Hooks（useAIContext + useAISuggestion）
3. **Task 5**: 前端 API 层
4. **Task 6-8**: 后端（Schema + Agent + 端点）
5. **Task 9**: AISuggestionCard 组件
6. **Task 10**: AIChatPanel 改造
7. **Task 11-12**: AppShell + App.tsx 路由
8. **Task 13-14**: CaseWizard + StepContent 联动
9. **Task 15**: 端到端测试

---

*计划版本: v1.0*
*生成日期: 2026-04-14*
