import React, { useState, useRef, useEffect } from 'react'
import { useCaseStore, AIMessage } from '../../stores/caseStore'
import { useAIContextStore } from '../../stores/aiContextStore'
import { useAISuggestion } from '../../hooks/useAISuggestion'
import { AISuggestionCard } from './AISuggestionCard'

export function AIChatPanel() {
  const { caseId, aiMessages, addAIMessage, pendingSuggestions } = useCaseStore()
  const { isAnalyzing } = useAIContextStore()

  const [message, setMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [aiMessages, pendingSuggestions])

  const handleSend = async () => {
    if (!message.trim() || isSending || !caseId) return

    const userMessage = message.trim()
    setMessage('')
    setIsSending(true)

    addAIMessage({ id: `msg_${Date.now()}`, role: 'user', content: userMessage, timestamp: Date.now() })

    try {
      const { aiService } = await import('../../services/aiService')
      // 用户主动聊天时，将当前案件上下文一并发送
      const result = await aiService.review({ caseId }, userMessage)
      addAIMessage({
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: result.review || '收到您的问题，请稍候。',
        timestamp: Date.now()
      })
    } catch {
      addAIMessage({ id: `msg_${Date.now()}`, role: 'assistant', content: '抱歉，发生了错误，请稍后再试。', timestamp: Date.now() })
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '320px', borderLeft: '1px solid #e0e0e0', backgroundColor: '#fafafa' }}>
      {/* Header */}
      <div style={{ padding: '16px', borderBottom: '1px solid #e0e0e0', backgroundColor: 'white' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '20px' }}>🤖</span>
          <span style={{ fontWeight: 600, fontSize: '16px' }}>AI 助手</span>
        </div>
        {isAnalyzing && <div style={{ marginTop: '8px', fontSize: '12px', color: '#667eea' }}>分析中...</div>}
      </div>

      {/* Chat History */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {aiMessages.length === 0 && !isAnalyzing && (
          <div style={{ textAlign: 'center', color: '#999', padding: '32px 16px', fontSize: '14px' }}>
            完成当前步骤后，AI 将自动分析并提供建议
          </div>
        )}

        {aiMessages.map((msg) => <ChatMessage key={msg.id} message={msg} />)}

        {pendingSuggestions.length > 0 && aiMessages.length > 0 && (
          <div style={{ marginTop: '8px' }}>
            <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>💡 发现以下可优化项：</div>
            {pendingSuggestions.map((s) => <AISuggestionCard key={s.id} suggestion={s} />)}
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div style={{ padding: '12px', borderTop: '1px solid #e0e0e0', backgroundColor: 'white' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text" value={message} onChange={(e) => setMessage(e.target.value)}
            placeholder="输入您的问题..." onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            disabled={isSending}
            style={{ flex: 1, padding: '10px 12px', borderRadius: '8px', border: '1px solid #ddd', fontSize: '14px', outline: 'none' }}
          />
          <button
            onClick={handleSend} disabled={isSending || !message.trim()}
            style={{ padding: '10px 16px', borderRadius: '8px', border: 'none', backgroundColor: '#667eea', color: 'white', fontSize: '14px', cursor: isSending ? 'not-allowed' : 'pointer', opacity: isSending ? 0.7 : 1 }}
          >
            {isSending ? '...' : '发送'}
          </button>
        </div>
      </div>
    </div>
  )
}

function ChatMessage({ message }: { message: AIMessage }) {
  const isUser = message.role === 'user'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start' }}>
      <div style={{
        maxWidth: '85%', padding: '10px 14px', borderRadius: isUser ? '12px 12px 0 12px' : '12px 12px 12px 0',
        backgroundColor: isUser ? '#667eea' : 'white', color: isUser ? 'white' : '#333', fontSize: '14px',
        lineHeight: 1.5, boxShadow: '0 1px 2px rgba(0,0,0,0.08)', whiteSpace: 'pre-wrap'
      }}>
        {message.content}
      </div>
      <span style={{ fontSize: '11px', color: '#bbb', marginTop: '4px' }}>
        {new Date(message.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
      </span>
    </div>
  )
}