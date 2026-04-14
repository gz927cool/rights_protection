import React, { useState } from 'react'
import { useAI } from '../../hooks/useAI'

interface AIChatPanelProps {
  caseId: string
}

export function AIChatPanel({ caseId }: AIChatPanelProps) {
  const [message, setMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<Array<{ role: string; content: string }>>([])
  const { review, isReviewing } = useAI()

  const handleSend = async () => {
    if (!message.trim()) return

    const userMessage = { role: 'user', content: message }
    setChatHistory((prev) => [...prev, userMessage])
    setMessage('')

    try {
      const result = await review({ caseData: {}, question: message })
      const aiMessage = { role: 'assistant', content: result.review }
      setChatHistory((prev) => [...prev, aiMessage])
    } catch (error) {
      const errorMessage = { role: 'assistant', content: '抱歉，发生了错误。' }
      setChatHistory((prev) => [...prev, errorMessage])
    }
  }

  return (
    <div className="ai-chat-panel">
      <h2>AI 复核</h2>
      <div className="chat-history">
        {chatHistory.map((msg, index) => (
          <div key={index} className={`chat-message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
      </div>
      <div className="chat-input">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="输入您的问题..."
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        />
        <button onClick={handleSend} disabled={isReviewing}>
          {isReviewing ? '发送中...' : '发送'}
        </button>
      </div>
    </div>
  )
}
