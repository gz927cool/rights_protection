import { useMutation } from '@tanstack/react-query'
import { aiService } from '../services/aiService'

export function useAI() {
  const analyzeCaseMutation = useMutation({
    mutationFn: (caseId: string) => aiService.analyzeCase(caseId)
  })

  const evaluateEvidenceMutation = useMutation({
    mutationFn: (evidenceId: string) => aiService.evaluateEvidence(evidenceId)
  })

  const assessRiskMutation = useMutation({
    mutationFn: (caseId: string) => aiService.assessRisk(caseId)
  })

  const generateDocumentMutation = useMutation({
    mutationFn: ({ caseId, documentType }: { caseId: string; documentType: string }) =>
      aiService.generateDocument(caseId, documentType)
  })

  const reviewMutation = useMutation({
    mutationFn: ({ caseData, question }: { caseData: object; question?: string }) =>
      aiService.review(caseData, question)
  })

  return {
    analyzeCase: analyzeCaseMutation.mutateAsync,
    analyzeCaseResult: analyzeCaseMutation.data,
    isAnalyzing: analyzeCaseMutation.isPending,

    evaluateEvidence: evaluateEvidenceMutation.mutateAsync,
    evidenceResult: evaluateEvidenceMutation.data,
    isEvaluating: evaluateEvidenceMutation.isPending,

    assessRisk: assessRiskMutation.mutateAsync,
    riskResult: assessRiskMutation.data,
    isAssessing: assessRiskMutation.isPending,

    generateDocument: generateDocumentMutation.mutateAsync,
    documentResult: generateDocumentMutation.data,
    isGenerating: generateDocumentMutation.isPending,

    review: reviewMutation.mutateAsync,
    reviewResult: reviewMutation.data,
    isReviewing: reviewMutation.isPending
  }
}
