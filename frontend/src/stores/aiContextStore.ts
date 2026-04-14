import { create } from 'zustand'

export interface AIContextState {
  isAnalyzing: boolean
  lastAnalyzedAt: number | null
  analyzingStep: number | null

  setAnalyzing: (step: number) => void
  setAnalyzed: () => void
  reset: () => void
}

export const useAIContextStore = create<AIContextState>((set) => ({
  isAnalyzing: false,
  lastAnalyzedAt: null,
  analyzingStep: null,

  setAnalyzing: (step) => set({ isAnalyzing: true, analyzingStep: step }),

  setAnalyzed: () =>
    set({ isAnalyzing: false, analyzingStep: null, lastAnalyzedAt: Date.now() }),

  reset: () => set({ isAnalyzing: false, lastAnalyzedAt: null, analyzingStep: null })
}))