import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { evidence as evidenceApi } from '../../services/api'

interface EvidenceStatusBoardProps {
  caseId: string
}

const statusColors: Record<string, string> = {
  A: 'green',
  B: 'yellow',
  C: 'red'
}

export function EvidenceStatusBoard({ caseId }: EvidenceStatusBoardProps) {
  const { data: evidenceList, refetch } = useQuery({
    queryKey: ['evidence', caseId],
    queryFn: () => evidenceApi.list(caseId).then(res => res.data),
    enabled: !!caseId
  })

  const getCompletenessLevel = () => {
    if (!evidenceList?.length) return '严重缺乏'
    const typeACount = evidenceList.filter((e: { type: string }) => e.type === 'A').length
    const total = evidenceList.length
    const ratio = typeACount / total
    if (ratio >= 0.8) return '充分'
    if (ratio >= 0.5) return '不完整'
    if (ratio >= 0.2) return '缺乏'
    return '严重缺乏'
  }

  return (
    <div className="evidence-status-board">
      <div className="board-header">
        <h3>证据清单</h3>
        <span className={`level level-${getCompletenessLevel()}`}>
          {getCompletenessLevel()}
        </span>
      </div>

      <div className="evidence-list">
        {evidenceList?.map((ev: {
          id: string
          type: string
          name: string
          ai_evaluation?: { completeness_score: number }
        }) => (
          <div key={ev.id} className="evidence-item">
            <span className={`badge badge-${statusColors[ev.type] || 'gray'}`}>
              {ev.type}
            </span>
            <span className="evidence-name">{ev.name}</span>
            {ev.ai_evaluation && (
              <span className="evidence-score">
                {ev.ai_evaluation.completeness_score}%
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
