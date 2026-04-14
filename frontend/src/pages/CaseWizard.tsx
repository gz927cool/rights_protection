import React from 'react'
import { StepWizard } from '../components/layout/StepWizard'
import { StepContent } from '../components/layout/StepContent'
import { useCaseStore } from '../stores/caseStore'
import { useStep } from '../hooks/useStep'

export function CaseWizard() {
  const { currentStep, nextStep, prevStep, canGoNext, canGoPrev } = useStep()
  const { status } = useCaseStore()

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
