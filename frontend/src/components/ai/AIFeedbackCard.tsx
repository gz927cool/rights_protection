import React from 'react'
import { useAI } from '../../hooks/useAI'
import { useCaseStore } from '../../stores/caseStore'

interface AIFeedbackCardProps {
  title: string
}

export function AIFeedbackCard({ title }: AIFeedbackCardProps) {
  const { caseId } = useCaseStore()
  const { analyzeCase, assessRisk, analyzeCaseResult, riskResult, isAnalyzing, isAssessing } = useAI()

  const handleAnalyze = async () => {
    if (!caseId) return
    if (title === '案情分析') {
      await analyzeCase(caseId)
    } else {
      await assessRisk(caseId)
    }
  }

  const result = title === '案情分析' ? analyzeCaseResult : riskResult

  return (
    <div className="ai-feedback-card">
      <h2>{title}</h2>
      <button onClick={handleAnalyze} disabled={isAnalyzing || isAssessing || !caseId}>
        {isAnalyzing || isAssessing ? '分析中...' : '开始分析'}
      </button>
      {result && (
        <div className="feedback-result">
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
