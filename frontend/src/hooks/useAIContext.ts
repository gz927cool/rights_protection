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
   * 构建发送给 AI 的上下文数据
   */
  const buildContextData = useCallback(() => {
    const answersThisStep = (stepData[currentStep] || {}) as Record<string, unknown>

    // 构建前置步骤摘要：遍历所有已完成步骤
    const previousStepsSummary: Record<string, Record<string, unknown>> = {}
    for (let s = 1; s < currentStep; s++) {
      const sData = stepData[s]
      if (sData && Object.keys(sData).length > 0) {
        previousStepsSummary[`step${s}`] = sData
      }
    }

    return {
      step_label: STEP_LABELS[currentStep - 1],
      case_summary: caseSummary,
      answers_this_step: answersThisStep,
      previous_steps_summary: previousStepsSummary,
      // evidence_status 由后端在 contextual-analysis 端点中补充
      user_question: null
    }
  }, [currentStep, stepData, caseSummary])

  /**
   * 触发 AI 上下文分析
   * 在步骤完成时调用（点击"下一步"时）
   */
  const analyzeCurrentStep = useCallback(async () => {
    if (!caseId || pendingSuggestions.length > 0) {
      return
    }

    setAnalyzing(currentStep)

    try {
      const contextData = buildContextData()

      const result = await aiService.contextualAnalysis({
        caseId,
        currentStep,
        contextData
      })

      if (result.case_summary) {
        setCaseSummary(result.case_summary)
      }

      addAIMessage({
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: result.analysis,
        suggestions: result.suggestions || [],
        timestamp: Date.now()
      })

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
  }, [caseId, currentStep, buildContextData, pendingSuggestions.length, setAnalyzing, setAnalyzed, setCaseSummary, addAIMessage, setPendingSuggestions])

  return {
    analyzeCurrentStep,
    buildContextData
  }
}