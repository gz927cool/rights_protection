import React from 'react'
import { useAISuggestion } from '../../hooks/useAISuggestion'
import { AISuggestion } from '../../stores/caseStore'

interface AISuggestionCardProps {
  suggestion: AISuggestion
}

const TYPE_LABELS: Record<string, { icon: string; label: string }> = {
  field_correction: { icon: '✏️', label: '字段修正' },
  missing_info: { icon: '📋', label: '补充信息' },
  risk_alert: { icon: '⚠️', label: '风险提示' },
  calculation: { icon: '🔢', label: '金额计算' }
}

export function AISuggestionCard({ suggestion }: AISuggestionCardProps) {
  const { accept, dismiss } = useAISuggestion()
  const typeInfo = TYPE_LABELS[suggestion.type] || { icon: '💡', label: '建议' }
  const showAiTag = suggestion.confidence < 0.9

  const formatValue = (value: unknown): string => {
    if (typeof value === 'number') return value.toLocaleString('zh-CN')
    return String(value)
  }

  return (
    <div style={{ border: '1px solid #e0e0e0', borderRadius: '8px', padding: '12px', marginBottom: '8px', backgroundColor: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
        <span>{typeInfo.icon}</span>
        <span style={{ fontWeight: 500, fontSize: '14px' }}>{typeInfo.label}</span>
        {showAiTag && (
          <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', backgroundColor: '#f0f0ff', color: '#667eea' }}>
            AI参考
          </span>
        )}
      </div>
      <div style={{ marginBottom: '8px' }}>
        <span style={{ color: '#666', fontSize: '13px' }}>{suggestion.fieldLabel}: </span>
        <span style={{ fontWeight: 500, fontSize: '14px', color: '#333' }}>{formatValue(suggestion.suggestedValue)}</span>
      </div>
      <div style={{ fontSize: '12px', color: '#888', marginBottom: '10px', lineHeight: 1.4 }}>
        {suggestion.reason}
      </div>
      <div style={{ display: 'flex', gap: '8px' }}>
        <button onClick={() => accept(suggestion.id)} style={{ flex: 1, padding: '6px 12px', borderRadius: '6px', border: 'none', backgroundColor: '#667eea', color: 'white', fontSize: '13px', cursor: 'pointer' }}>确认</button>
        <button onClick={() => dismiss(suggestion.id)} style={{ flex: 1, padding: '6px 12px', borderRadius: '6px', border: '1px solid #ddd', backgroundColor: 'white', color: '#666', fontSize: '13px', cursor: 'pointer' }}>忽略</button>
      </div>
    </div>
  )
}