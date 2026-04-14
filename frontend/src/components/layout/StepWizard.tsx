import React from 'react'
import { useStep } from '../../hooks/useStep'

export function StepWizard() {
  const { currentStep, stepLabels, goToStep } = useStep()

  return (
    <div className="step-wizard">
      <div className="steps">
        {stepLabels.map((label, index) => {
          const stepNum = index + 1
          const isActive = stepNum === currentStep
          const isCompleted = stepNum < currentStep

          return (
            <React.Fragment key={stepNum}>
              <button
                className={`step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
                onClick={() => goToStep(stepNum)}
                disabled={stepNum > currentStep}
              >
                <span className="step-number">{stepNum}</span>
                <span className="step-label">{label}</span>
              </button>
              {index < stepLabels.length - 1 && (
                <div className={`connector ${isCompleted ? 'connector-completed' : ''}`} />
              )}
            </React.Fragment>
          )
        })}
      </div>
    </div>
  )
}
