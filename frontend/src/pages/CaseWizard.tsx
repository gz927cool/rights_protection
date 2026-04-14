import React, { useEffect } from 'react'
import { StepWizard } from '../components/layout/StepWizard'
import { StepContent } from '../components/layout/StepContent'
import { useCaseStore } from '../stores/caseStore'
import { useStep } from '../hooks/useStep'
import { useAIContext } from '../hooks/useAIContext'

export function CaseWizard() {
  const { nextStep, prevStep, canGoNext, canGoPrev } = useStep()
  const { status, currentStep } = useCaseStore()
  const { analyzeCurrentStep } = useAIContext()

  // 当 currentStep 变化时（用户点击"下一步"），触发 AI 分析
  useEffect(() => {
    if (currentStep > 1) {
      analyzeCurrentStep()
    }
  }, [currentStep])

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
          <button className="btn-primary" onClick={nextStep} disabled={status === 'loading'}>
            下一步
          </button>
        )}
      </div>
    </div>
  )
}