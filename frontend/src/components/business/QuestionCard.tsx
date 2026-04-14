import React, { useState } from 'react'

interface QuestionCardProps {
  step: number
}

const questions = {
  2: [
    { id: 'q1', text: '您的入职时间？', type: 'date' },
    { id: 'q2', text: '您的工作岗位？', type: 'select', options: ['普通员工', '外卖员', '网约车司机', '其他'] },
    { id: 'q3', text: '涉及金额？', type: 'number' }
  ],
  3: [
    { id: 'sq1', text: '具体发生了什么？', type: 'text' }
  ]
}

export function QuestionCard({ step }: QuestionCardProps) {
  const [answers, setAnswers] = useState<Record<string, unknown>>({})

  const handleAnswer = (questionId: string, value: unknown) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }))
  }

  const stepQuestions = questions[step as keyof typeof questions] || []

  return (
    <div className="question-card">
      <h2>请回答以下问题</h2>
      {stepQuestions.map((q) => (
        <div key={q.id} className="question-item">
          <label>{q.text}</label>
          {q.type === 'select' && (
            <select
              value={(answers[q.id] as string) || ''}
              onChange={(e) => handleAnswer(q.id, e.target.value)}
            >
              <option value="">请选择</option>
              {(q as { options: string[] }).options.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          )}
          {q.type === 'date' && (
            <input
              type="date"
              value={(answers[q.id] as string) || ''}
              onChange={(e) => handleAnswer(q.id, e.target.value)}
            />
          )}
          {q.type === 'number' && (
            <input
              type="number"
              value={(answers[q.id] as number) || ''}
              onChange={(e) => handleAnswer(q.id, Number(e.target.value))}
            />
          )}
          {q.type === 'text' && (
            <textarea
              value={(answers[q.id] as string) || ''}
              onChange={(e) => handleAnswer(q.id, e.target.value)}
            />
          )}
        </div>
      ))}
    </div>
  )
}
