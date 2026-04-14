import React from 'react'
import { useStep } from '../../hooks/useStep'
import { CauseSelector } from '../business/CauseSelector'
import { QuestionCard } from '../business/QuestionCard'
import { AIChatPanel } from '../ai/AIChatPanel'
import { AIFeedbackCard } from '../ai/AIFeedbackCard'
import { useCaseStore } from '../../stores/caseStore'

export function StepContent() {
  const { currentStep } = useStep()
  const { caseId } = useCaseStore()

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return <CauseSelector />
      case 2:
      case 3:
        return <QuestionCard step={currentStep} />
      case 4:
      case 6:
        return <AIFeedbackCard title={currentStep === 4 ? "案情分析" : "风险评估"} />
      case 9:
        return <AIChatPanel caseId={caseId || ''} />
      default:
        return <div className="placeholder">该步骤功能开发中</div>
    }
  }

  return <div className="step-content">{renderStep()}</div>
}
