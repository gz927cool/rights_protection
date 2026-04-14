import { useCaseStore } from '../stores/caseStore'
import { cases as casesApi } from '../services/api'

export function useStep() {
  const { caseId, currentStep, setStep } = useCaseStore()

  const stepLabels = [
    '模式选择', '问题初判', '信息补全', '案件定性',
    '证据攻略', '风险提示', '文书生成', '行动路线图', '求助复核'
  ]

  const goToStep = async (step: number) => {
    if (!caseId) return
    await casesApi.updateStep(caseId, step)
    setStep(step)
  }

  const nextStep = () => goToStep(currentStep + 1)
  const prevStep = () => goToStep(currentStep - 1)

  return {
    currentStep,
    stepLabels,
    goToStep,
    nextStep,
    prevStep,
    canGoNext: currentStep < 9,
    canGoPrev: currentStep > 1
  }
}
