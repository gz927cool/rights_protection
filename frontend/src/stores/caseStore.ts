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
