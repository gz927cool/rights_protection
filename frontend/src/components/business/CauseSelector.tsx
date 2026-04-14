import React from 'react'

const causes = [
  { id: '欠薪', label: '欠薪', icon: '💰' },
  { id: '开除', label: '开除', icon: '📋' },
  { id: '工伤', label: '工伤', icon: '🏥' },
  { id: '调岗', label: '调岗', icon: '📍' },
  { id: '社保', label: '社保', icon: '🏛️' },
  { id: '其他', label: '其他', icon: '📝' }
]

export function CauseSelector() {
  const handleSelect = (causeId: string) => {
    console.log('Selected cause:', causeId)
    // TODO: 保存选择，触发下一步
  }

  return (
    <div className="cause-selector">
      <h2>请选择您的问题类型</h2>
      <div className="cause-grid">
        {causes.map((cause) => (
          <button
            key={cause.id}
            className="cause-button"
            onClick={() => handleSelect(cause.id)}
          >
            <span className="cause-icon">{cause.icon}</span>
            <span className="cause-label">{cause.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
