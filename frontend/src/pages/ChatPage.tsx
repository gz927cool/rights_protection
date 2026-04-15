import { useState, useEffect, useRef, useCallback } from "react"
import { useParams, Link } from "react-router-dom"

interface Message {
  role: "user" | "assistant"
  content: string
}

interface SessionState {
  current_step: number
  current_step_name: string
  completed_steps: number[]
}

const STEP_LABELS = [
  "模式选择", "问题初判", "通用问题", "特殊问题", "案件定性",
  "证据攻略", "风险提示", "文书生成", "行动路线图", "求助复核",
]

export default function ChatPage() {
  const { sessionId } = useParams()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [sessionState, setSessionState] = useState<SessionState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const currentSessionId = sessionId || "new"

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Fetch session state
  useEffect(() => {
    if (!currentSessionId || currentSessionId === "new") return
    fetch(`/sessions/${currentSessionId}`)
      .then(r => r.json())
      .then(data => {
        if (data && data.current_step) {
          setSessionState(data)
        }
      })
      .catch(() => {})
  }, [currentSessionId])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = { role: "user", content: input }
    setMessages(prev => [...prev, userMessage])
    const userInput = input
    setInput("")
    setLoading(true)
    setError(null)

    try {
      const res = await fetch("/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: userInput, session_id: currentSessionId }),
      })

      if (!res.ok) {
        throw new Error(`服务器响应错误: ${res.status} ${res.statusText}`)
      }

      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let fullContent = ""
      let finalStep = 1

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          const chunk = decoder.decode(value, { stream: true })
          for (const line of chunk.split("\n")) {
            if (!line.startsWith("data: ")) continue
            try {
              const data = JSON.parse(line.slice(6))
              if (data.content) {
                fullContent += data.content
              }
              if (data.done) {
                finalStep = data.current_step || finalStep
              }
              if (data.session_id && data.session_id !== currentSessionId) {
                // New session created, redirect
                window.history.replaceState(null, "", `/chat/${data.session_id}`)
              }
            } catch (parseErr) {
              console.error("解析流数据失败:", parseErr, "原始数据:", line)
            }
          }
        }

        // Update messages once after all chunks collected to prevent race conditions
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last?.role === "assistant") {
            return [...prev.slice(0, -1), { ...last, content: fullContent }]
          }
          return [...prev, { role: "assistant", content: fullContent }]
        })
      }

      // Update session state after message
      if (currentSessionId !== "new") {
        fetch(`/sessions/${currentSessionId}`)
          .then(r => r.json())
          .then(setSessionState)
          .catch((stateErr) => {
            console.error("获取会话状态失败:", stateErr)
          })
      }
    } catch (err) {
      console.error("发送消息失败:", err)
      const errorMessage = err instanceof Error ? err.message : "网络连接失败，请检查后端服务是否正常运行"
      setError(errorMessage)

      // Add error message to chat
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `抱歉，发送消息时出现错误：${errorMessage}`
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-indigo-600 text-white px-4 py-3 flex items-center justify-between shadow-sm">
        <div>
          <h2 className="font-semibold">劳动争议咨询</h2>
          {sessionState && (
            <p className="text-xs text-indigo-200">
              第{sessionState.current_step}步 · {sessionState.current_step_name}
            </p>
          )}
        </div>
        <Link to="/" className="text-sm text-indigo-200 hover:text-white">
          返回首页
        </Link>
      </header>

      {/* Step Progress */}
      {sessionState && (
        <div className="bg-white border-b px-4 py-2">
          <div className="flex items-center gap-1 overflow-x-auto">
            {STEP_LABELS.map((label, i) => {
              const stepNum = i + 1
              const isCompleted = sessionState.completed_steps?.includes(stepNum)
              const isCurrent = sessionState.current_step === stepNum
              return (
                <div key={i} className="flex items-center">
                  <div className={`flex items-center gap-1 px-2 py-1 rounded text-xs whitespace-nowrap ${
                    isCurrent ? "bg-indigo-100 text-indigo-700 font-medium" :
                    isCompleted ? "bg-green-100 text-green-700" :
                    "text-gray-400"
                  }`}>
                    <span>{stepNum}</span>
                    <span>{label}</span>
                    {isCompleted && <span>✓</span>}
                  </div>
                  {i < STEP_LABELS.length - 1 && (
                    <div className="w-2 h-px bg-gray-300 mx-0.5" />
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 px-4 py-3 mx-4 mt-2">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3 flex-1">
              <p className="text-sm text-red-700">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="ml-3 flex-shrink-0 text-red-500 hover:text-red-700"
            >
              <span className="sr-only">关闭</span>
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-20">
            <div className="text-4xl mb-3">⚖️</div>
            <p className="font-medium text-gray-600">欢迎使用劳动争议智能咨询系统</p>
            <p className="text-sm mt-1">请描述您的劳动争议问题，AI助手将引导您完成维权流程</p>
            <div className="mt-6 text-left max-w-md mx-auto">
              <p className="text-xs text-gray-400 mb-2">常见问题类型：</p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {["欠薪/克扣工资", "被辞退/开除", "工伤认定", "调岗降薪", "社保欠缴", "其他争议"].map(cat => (
                  <button
                    key={cat}
                    onClick={() => setInput(`我想咨询${cat}问题`)}
                    className="bg-gray-100 hover:bg-gray-200 rounded px-2 py-1 text-gray-600 text-left"
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-xl rounded-2xl px-4 py-3 ${
              msg.role === "user"
                ? "bg-indigo-600 text-white rounded-br-md"
                : "bg-white border shadow-sm text-gray-800 rounded-bl-md"
            }`}>
              <pre className="whitespace-pre-wrap text-sm font-sans" style={{ fontFamily: "inherit" }}>
                {msg.content}
              </pre>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border rounded-2xl rounded-bl-md px-4 py-3 text-gray-500">
              <div className="flex gap-1">
                <span className="animate-bounce">●</span>
                <span className="animate-bounce" style={{ animationDelay: "0.2s" }}>●</span>
                <span className="animate-bounce" style={{ animationDelay: "0.4s" }}>●</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t bg-white p-4">
        <div className="flex gap-2 items-end max-w-3xl mx-auto">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                sendMessage()
              }
            }}
            placeholder="输入您的劳动争议问题..."
            rows={1}
            className="flex-1 border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
            style={{ maxHeight: "120px" }}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 font-medium transition-colors"
          >
            发送
          </button>
        </div>
        <p className="text-xs text-gray-400 text-center mt-2">
          按 Enter 发送，Shift+Enter 换行
        </p>
      </div>
    </div>
  )
}
