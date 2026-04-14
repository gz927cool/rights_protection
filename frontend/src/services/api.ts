import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' }
})

// Auth
export const auth = {
  login: (phone: string, code: string) =>
    client.post('/auth/login', { phone, code }),
  logout: () => client.post('/auth/logout')
}

// Cases
export const cases = {
  create: () => client.post('/cases', {}),
  get: (id: string) => client.get(`/cases/${id}`),
  updateStep: (id: string, step: number) =>
    client.put(`/cases/${id}/step/${step}`),
  getAnswers: (id: string) => client.get(`/cases/${id}/answers`),
  submitAnswer: (caseId: string, questionId: string, value: unknown) =>
    client.post(`/cases/${caseId}/answers`, { question_id: questionId, answer_value: value })
}

// Causes
export const causes = {
  list: () => client.get('/causes'),
  get: (id: string) => client.get(`/causes/${id}`),
  getQuestions: (id: string) => client.get(`/causes/${id}/questions`)
}

// Evidence
export const evidence = {
  upload: (caseId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return client.post(`/cases/${caseId}/evidence`, form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  list: (caseId: string) => client.get(`/cases/${caseId}/evidence`),
  delete: (id: string) => client.delete(`/evidence/${id}`)
}

// Documents
export const documents = {
  list: (caseId: string) => client.get(`/cases/${caseId}/documents`),
  get: (id: string) => client.get(`/documents/${id}`),
  export: (id: string, format: 'docx' | 'pdf') =>
    client.get(`/documents/${id}/export/${format}`, { responseType: 'blob' })
}

// AI
export const ai = {
  analyzeCase: (caseId: string) =>
    client.post('/ai/analyze-case', { case_id: caseId }),
  evaluateEvidence: (evidenceId: string) =>
    client.post('/ai/evaluate-evidence', { evidence_id: evidenceId }),
  assessRisk: (caseId: string) =>
    client.post('/ai/risk-assessment', { case_id: caseId }),
  generateDocument: (caseId: string, documentType: string) =>
    client.post('/ai/generate-document', { case_id: caseId, document_type: documentType }),
  review: (caseData: object, question?: string) =>
    client.post('/ai/review', { case_data: caseData, user_question: question }),
  contextualAnalysis: (params: {
    caseId: string
    currentStep: number
    contextData: Record<string, unknown>
  }) =>
    client.post('/ai/contextual-analysis', {
      case_id: params.caseId,
      current_step: params.currentStep,
      context_data: params.contextData
    })
}

export const api = { auth, cases, causes, evidence, documents, ai }
export default api
