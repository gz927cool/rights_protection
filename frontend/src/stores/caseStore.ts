import { create } from 'zustand'

interface CaseState {
  caseId: string | null
  currentStep: number
  status: 'idle' | 'loading' | 'success' | 'error'
  caseData: Record<string, unknown> | null
  setCaseId: (id: string | null) => void
  setStep: (step: number) => void
  setCaseData: (data: Record<string, unknown> | null) => void
  setStatus: (status: 'idle' | 'loading' | 'success' | 'error') => void
  reset: () => void
}

export const useCaseStore = create<CaseState>((set) => ({
  caseId: null,
  currentStep: 1,
  status: 'idle',
  caseData: null,
  setCaseId: (id) => set({ caseId: id }),
  setStep: (step) => set({ currentStep: Math.min(9, Math.max(1, step)) }),
  setCaseData: (data) => set({ caseData: data }),
  setStatus: (status) => set({ status }),
  reset: () => set({ caseId: null, currentStep: 1, status: 'idle', caseData: null })
}))
