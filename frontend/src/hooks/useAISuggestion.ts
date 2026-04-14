import { useCallback } from 'react'
import { useCaseStore } from '../stores/caseStore'

export function useAISuggestion() {
  const {
    pendingSuggestions,
    acceptSuggestion,
    dismissSuggestion,
    stepData,
    currentStep
  } = useCaseStore()

  const accept = useCallback((suggestionId: string) => {
    acceptSuggestion(suggestionId)
  }, [acceptSuggestion])

  const dismiss = useCallback((suggestionId: string) => {
    dismissSuggestion(suggestionId)
  }, [dismissSuggestion])

  const getPrefilledValue = useCallback((field: string): unknown => {
    const currentStepData = stepData[currentStep] || {}
    return currentStepData[field]
  }, [stepData, currentStep])

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