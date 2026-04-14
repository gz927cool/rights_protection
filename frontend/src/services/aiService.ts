import { ai } from './api'

export const aiService = {
  analyzeCase: async (caseId: string) => {
    const response = await ai.analyzeCase(caseId)
    return response.data
  },

  evaluateEvidence: async (evidenceId: string) => {
    const response = await ai.evaluateEvidence(evidenceId)
    return response.data
  },

  assessRisk: async (caseId: string) => {
    const response = await ai.assessRisk(caseId)
    return response.data
  },

  generateDocument: async (caseId: string, documentType: string = '仲裁申请书') => {
    const response = await ai.generateDocument(caseId, documentType)
    return response.data
  },

  review: async (caseData: object, question?: string) => {
    const response = await ai.review(caseData, question)
    return response.data
  }
}
