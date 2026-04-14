import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { cases as casesApi } from '../services/api'
import { useCaseStore } from '../stores/caseStore'

export function useCase() {
  const queryClient = useQueryClient()
  const { caseId, setCaseId, setCaseData, setStatus } = useCaseStore()

  const createCaseMutation = useMutation({
    mutationFn: () => casesApi.create(),
    onSuccess: (response) => {
      const newCase = response.data
      setCaseId(newCase.id)
      setCaseData(newCase)
      queryClient.invalidateQueries({ queryKey: ['case'] })
    }
  })

  const caseQuery = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => caseId ? casesApi.get(caseId) : null,
    enabled: !!caseId
  })

  return {
    caseId,
    caseData: caseQuery.data?.data,
    createCase: async () => {
      await createCaseMutation.mutateAsync()
    },
    isCreating: createCaseMutation.isPending,
    isLoading: caseQuery.isLoading
  }
}
