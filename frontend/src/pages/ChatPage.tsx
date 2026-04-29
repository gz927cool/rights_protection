import { useState, useEffect, useRef, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import InfoPanel, { InfoPanelProps } from "../components/InfoPanel"

// =============================================================================
// Types
// =============================================================================

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  streaming?: boolean
  artifactType?: "rights" | "risk" | "evidence" | "document" | "roadmap" | "form" | "tool_call"
  artifactData?: unknown
}

interface SessionState {
  current_step: number
  current_step_name: string
  completed_steps: number[]
  case_category?: string
  evidence_items?: EvidenceItem[]
  qualification?: unknown
  document_draft?: unknown
  risk_assessment?: unknown
}

interface EvidenceItem {
  id: string
  name: string
  description: string
  category: string
  tier: number
  status: "" | "A" | "B" | "C"
  uploaded_file_refs: string[]
}

interface StreamEvent {
  // OpenAI SSE event type
  event?: "content" | "tool_calls" | "tool_call_done" | "done"
  // content event
  content?: string
  role?: string
  // tool_calls event
  name?: string
  arguments?: Record<string, unknown>
  // tool_call_done event
  tool_call_id?: string
  result?: string
  // done event
  current_step?: number
  session_id?: string
  // Legacy / compatibility
  done?: boolean
  artifact_type?: string
  artifact_data?: unknown
  error?: string
}

interface RightsItem {
  right_name: string
  amount: number
  calculation_basis: string
}

interface RiskItem {
  level: "high" | "medium" | "low"
  title: string
  description: string
  suggestion: string
}

// =============================================================================
// Constants
// =============================================================================

const STEP_LABELS = [
  { num: 1, label: "问题初判", icon: "📋" },
  { num: 2, label: "通用问题", icon: "📝" },
  { num: 3, label: "特殊问题", icon: "🔍" },
  { num: 4, label: "案件定性", icon: "⚖️" },
  { num: 5, label: "证据攻略", icon: "📁" },
  { num: 6, label: "风险提示", icon: "⚠️" },
  { num: 7, label: "文书生成", icon: "📄" },
  { num: 8, label: "行动路线图", icon: "🗺️" },
  { num: 9, label: "求助复核", icon: "🆘" },
]

const THEME = {
  primary: "bg-blue-600",
  primaryLight: "bg-blue-50",
  primaryText: "text-blue-700",
  accent: "bg-emerald-600",
  accentLight: "bg-emerald-50",
  accentText: "text-emerald-700",
  warning: "bg-amber-50",
  warningText: "text-amber-700",
  danger: "bg-red-50",
  dangerText: "text-red-700",
  surface: "bg-white",
  surfaceAlt: "bg-gray-50",
  border: "border-gray-200",
  textPrimary: "text-gray-800",
  textSecondary: "text-gray-600",
  textMuted: "text-gray-400",
}

// =============================================================================
// Utility Components
// =============================================================================

function generateId() {
  return Math.random().toString(36).substring(2, 9)
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ")
}

// =============================================================================
// Step Indicator Component
// =============================================================================

function StepIndicator({
  currentStep,
  completedSteps,
  onStepClick,
}: {
  currentStep: number
  completedSteps: number[]
  onStepClick?: (step: number) => void
}) {
  return (
    <div className="w-full overflow-x-auto py-3 px-4">
      <div className="flex items-center gap-1 min-w-max">
        {STEP_LABELS.map((step, idx) => {
          const isCompleted = completedSteps.includes(step.num)
          const isCurrent = currentStep === step.num
          const isClickable = isCompleted || isCurrent

          return (
            <div key={step.num} className="flex items-center">
              <button
                onClick={() => isClickable && onStepClick?.(step.num)}
                disabled={!isClickable}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  isCurrent && "ring-2 ring-blue-400 shadow-sm",
                  isCompleted && THEME.accentLight + " " + THEME.accentText,
                  isCurrent && THEME.primaryLight + " " + THEME.primaryText,
                  !isCompleted && !isCurrent && "bg-gray-100 text-gray-400"
                )}
              >
                <span className="text-base">{step.icon}</span>
                <span className="hidden sm:inline">{step.label}</span>
                <span className="sm:hidden">{step.num}</span>
                {isCompleted && (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </button>
              {idx < STEP_LABELS.length - 1 && (
                <div className="w-4 h-px bg-gray-200 mx-0.5" />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// =============================================================================
// Streaming Text Component
// =============================================================================

function StreamingText({ text }: { text: string }) {
  return (
    <div className="relative">
      <pre className="whitespace-pre-wrap text-sm font-sans leading-relaxed">
        {text}
        <span className="inline-block w-2 h-4 bg-blue-500 animate-pulse ml-1" />
      </pre>
    </div>
  )
}

// =============================================================================
// Rights Summary Table
// =============================================================================

function RightsSummaryTable({ rights }: { rights: RightsItem[] }) {
  const total = rights.reduce((sum, r) => sum + (r.amount || 0), 0)

  return (
    <div className="my-4 rounded-xl border border-gray-200 overflow-hidden">
      <div className="bg-blue-50 px-4 py-3 border-b border-gray-200">
        <h4 className="font-semibold text-blue-800 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
          权益清单
        </h4>
      </div>
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-gray-600">权益项目</th>
            <th className="px-4 py-2 text-right font-medium text-gray-600">金额</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rights.map((item, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="px-4 py-2 text-gray-700">{item.right_name}</td>
              <td className="px-4 py-2 text-right font-semibold text-gray-800">
                ¥{(item.amount || 0).toLocaleString("zh-CN")}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-blue-50">
          <tr>
            <td className="px-4 py-3 font-bold text-blue-800">合计</td>
            <td className="px-4 py-3 text-right font-bold text-blue-800 text-lg">
              ¥{total.toLocaleString("zh-CN")}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

// =============================================================================
// Risk Assessment Display
// =============================================================================

function RiskAssessmentDisplay({ risks }: { risks: RiskItem[] }) {
  const getRiskStyle = (level: string) => {
    switch (level) {
      case "high":
        return { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", icon: "⚠️" }
      case "medium":
        return { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", icon: "⚡" }
      default:
        return { bg: "bg-green-50", border: "border-green-200", text: "text-green-700", icon: "✓" }
    }
  }

  const highRisks = risks.filter((r) => r.level === "high")

  return (
    <div className="my-4 space-y-3">
      <div className="flex items-center gap-2 mb-4">
        <h4 className="font-semibold text-gray-800 flex items-center gap-2">
          <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          风险提示
        </h4>
        {highRisks.length > 0 && (
          <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full">
            {highRisks.length} 高风险
          </span>
        )}
      </div>

      {risks.map((risk, i) => {
        const style = getRiskStyle(risk.level)
        return (
          <div
            key={i}
            className={cn("rounded-lg border p-4", style.bg, style.border)}
          >
            <div className="flex items-start gap-3">
              <span className="text-xl">{style.icon}</span>
              <div className="flex-1">
                <h5 className={cn("font-medium", style.text)}>{risk.title}</h5>
                <p className="text-sm text-gray-600 mt-1">{risk.description}</p>
                {risk.suggestion && (
                  <div className="mt-2 text-sm text-gray-500">
                    <span className="font-medium">建议：</span>
                    {risk.suggestion}
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// =============================================================================
// Quick Action Buttons
// =============================================================================

const QUICK_CATEGORIES = [
  { label: "欠薪/克扣工资", icon: "💰" },
  { label: "被辞退/开除", icon: "🚫" },
  { label: "工伤认定", icon: "🏥" },
  { label: "调岗降薪", icon: "📉" },
  { label: "社保欠缴", icon: "🏦" },
  { label: "其他争议", icon: "❓" },
]

// [已屏蔽] 快捷问题类型组件 - 保留代码以便以后恢复
const _QuickActions = QuickActions;
void _QuickActions; // eslint-disable-line @typescript-eslint/no-unused-vars
function QuickActions({ onSelect }: { onSelect: (action: string) => void }) {

  return (
    <div className="my-4">
      <p className="text-xs text-gray-500 mb-2">快捷问题类型：</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {QUICK_CATEGORIES.map((cat) => (
          <button
            key={cat.label}
            onClick={() => onSelect(`我想咨询${cat.label}问题`)}
            className="flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm text-gray-700 border border-gray-200 transition-colors"
          >
            <span>{cat.icon}</span>
            <span>{cat.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Rich Message Renderer
// =============================================================================

function parseMessageContent(content: string): {
  text: string
  artifactType?: string
  artifactData?: unknown
} {
  // Handle TOOL_CALL markers first — extract interactive component specs
  const toolCallMatch = content.match(/\[TOOL_CALL:(\w+)\]([\s\S]*?)\[\/TOOL_CALL\]/)
  if (toolCallMatch) {
    const toolName = toolCallMatch[1]
    try {
      const args = JSON.parse(toolCallMatch[2])
      return {
        text: content.replace(/\[TOOL_CALL:\w+\][\s\S]*?\[\/TOOL_CALL\]/, "").trim(),
        artifactType: "tool_call",
        artifactData: { name: toolName, ...args },
      }
    } catch {
      return { text: content.replace(/\[TOOL_CALL:\w+\][\s\S]*?\[\/TOOL_CALL\]/, "").trim() }
    }
  }

  // Handle SELECT_OPTION markers — [SELECT_OPTION]{...}[/SELECT_OPTION]
  const selectOptionMatch = content.match(/\[SELECT_OPTION\]([\s\S]*?)\[\/SELECT_OPTION\]/)
  if (selectOptionMatch) {
    try {
      const args = JSON.parse(selectOptionMatch[1])
      return {
        text: content.replace(/\[SELECT_OPTION\][\s\S]*?\[\/SELECT_OPTION\]/, "").trim(),
        artifactType: "tool_call",
        artifactData: { name: "select_option", ...args },
      }
    } catch {
      return { text: content.replace(/\[SELECT_OPTION\][\s\S]*?\[\/SELECT_OPTION\]/, "").trim() }
    }
  }

  // Handle TEXT_INPUT markers — [TEXT_INPUT]{...}[/TEXT_INPUT]
  const textInputMatch = content.match(/\[TEXT_INPUT\]([\s\S]*?)\[\/TEXT_INPUT\]/)
  if (textInputMatch) {
    try {
      const args = JSON.parse(textInputMatch[1])
      return {
        text: content.replace(/\[TEXT_INPUT\][\s\S]*?\[\/TEXT_INPUT\]/, "").trim(),
        artifactType: "tool_call",
        artifactData: { name: "text_input", ...args },
      }
    } catch {
      return { text: content.replace(/\[TEXT_INPUT\][\s\S]*?\[\/TEXT_INPUT\]/, "").trim() }
    }
  }

  // Handle DATE_PICKER markers — [DATE_PICKER]{...}[/DATE_PICKER]
  const datePickerMatch = content.match(/\[DATE_PICKER\]([\s\S]*?)\[\/DATE_PICKER\]/)
  if (datePickerMatch) {
    try {
      const args = JSON.parse(datePickerMatch[1])
      return {
        text: content.replace(/\[DATE_PICKER\][\s\S]*?\[\/DATE_PICKER\]/, "").trim(),
        artifactType: "tool_call",
        artifactData: { name: "date_picker", ...args },
      }
    } catch {
      return { text: content.replace(/\[DATE_PICKER\][\s\S]*?\[\/DATE_PICKER\]/, "").trim() }
    }
  }

  // Handle NUMBER_INPUT markers — [NUMBER_INPUT]{...}[/NUMBER_INPUT]
  const numberInputMatch = content.match(/\[NUMBER_INPUT\]([\s\S]*?)\[\/NUMBER_INPUT\]/)
  if (numberInputMatch) {
    try {
      const args = JSON.parse(numberInputMatch[1])
      return {
        text: content.replace(/\[NUMBER_INPUT\][\s\S]*?\[\/NUMBER_INPUT\]/, "").trim(),
        artifactType: "tool_call",
        artifactData: { name: "number_input", ...args },
      }
    } catch {
      return { text: content.replace(/\[NUMBER_INPUT\][\s\S]*?\[\/NUMBER_INPUT\]/, "").trim() }
    }
  }

  // Strip tool command JSON from display (e.g. {"tool":"proceed_to_next_step",...})
  let cleanContent = content.replace(/\{[^{}]*"tool"\s*:[^{}]*\}/g, "").trim()
  // Strip any remaining trailing tool JSON blocks
  cleanContent = cleanContent.replace(/\n\s*\{[^{}]*"[^"]+"\s*:[^}]+\}\s*$/, "").trim()

  if (cleanContent.includes("[RIGHTS_DATA]")) {
    try {
      const jsonMatch = cleanContent.match(/\[RIGHTS_DATA\]([\s\S]*?)\[\/RIGHTS_DATA\]/)
      if (jsonMatch) {
        const rights = JSON.parse(jsonMatch[1]) as RightsItem[]
        return {
          text: cleanContent.replace(/\[RIGHTS_DATA\][\s\S]*?\[\/RIGHTS_DATA\]/, "").trim(),
          artifactType: "rights",
          artifactData: rights,
        }
      }
    } catch {}
  }

  if (cleanContent.includes("[RISK_DATA]")) {
    try {
      const jsonMatch = cleanContent.match(/\[RISK_DATA\]([\s\S]*?)\[\/RISK_DATA\]/)
      if (jsonMatch) {
        const risks = JSON.parse(jsonMatch[1]) as RiskItem[]
        return {
          text: cleanContent.replace(/\[RISK_DATA\][\s\S]*?\[\/RISK_DATA\]/, "").trim(),
          artifactType: "risk",
          artifactData: risks,
        }
      }
    } catch {}
  }

  if (cleanContent.includes("[EVIDENCE_FORM]")) {
    return {
      text: cleanContent.replace("[EVIDENCE_FORM]", "").trim(),
      artifactType: "evidence",
    }
  }

  if (cleanContent.includes("[DOCUMENT_PREVIEW]")) {
    return {
      text: cleanContent.replace("[DOCUMENT_PREVIEW]", "").trim(),
      artifactType: "document",
    }
  }

  if (cleanContent.includes("[ROADMAP]")) {
    return {
      text: cleanContent.replace("[ROADMAP]", "").trim(),
      artifactType: "roadmap",
    }
  }

  return { text: cleanContent }
}

function RichMessageRenderer({ message, onQuickAction }: { message: Message; onQuickAction?: (text: string) => void }) {
  const { text, artifactType, artifactData } = parseMessageContent(message.content)

  if (message.role === "user") {
    return (
      <div className="max-w-xl rounded-2xl px-4 py-3 bg-blue-600 text-white rounded-br-md">
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Main text content */}
      {text && (
        <div className="bg-white border rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
          {message.streaming ? (
            <StreamingText text={text} />
          ) : (
            <div className="markdown-content prose prose-sm max-w-none prose-p:my-1 prose-li:my-0.5 prose-headings:my-2 prose-hr:my-3">
              {text ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {text}
                </ReactMarkdown>
              ) : null}
            </div>
          )}
        </div>
      )}

      {/* Artifact rendering based on type */}
      {artifactType === "rights" && artifactData !== undefined ? (
        <RightsSummaryTable rights={artifactData as RightsItem[]} />
      ) : null}

      {artifactType === "risk" && artifactData !== undefined ? (
        <RiskAssessmentDisplay risks={artifactData as RiskItem[]} />
      ) : null}

      {/* Interactive tool_call component */}
      {artifactType === "tool_call" && artifactData !== undefined ? (() => {
        const td = artifactData as { name: string; question?: string; options?: string[]; placeholder?: string; multiline?: boolean; min?: number; max?: number; unit?: string }
        if (td.name === "select_option" && td.options) {
          return (
            <div className="flex flex-wrap gap-2 p-3 bg-white border rounded-xl">
              {td.options.map((opt, i) => (
                <button
                  key={i}
                  onClick={() => onQuickAction?.(opt)}
                  className="px-4 py-2 rounded-full border border-blue-200 text-blue-700 text-sm hover:bg-blue-50 transition-colors"
                >
                  {opt}
                </button>
              ))}
            </div>
          )
        }
        if (td.name === "text_input") {
          return (
            <div className="p-3 bg-white border rounded-xl">
              <p className="text-sm text-gray-600 mb-2">{td.question}</p>
              <textarea
                placeholder={td.placeholder}
                rows={td.multiline ? 3 : 1}
                className="w-full border rounded-lg px-3 py-2 text-sm"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !td.multiline) {
                    e.preventDefault()
                    onQuickAction?.((e.target as HTMLTextAreaElement).value)
                  }
                }}
              />
            </div>
          )
        }
        if (td.name === "date_picker") {
          return (
            <div className="p-3 bg-white border rounded-xl">
              <p className="text-sm text-gray-600 mb-2">{td.question}</p>
              <input
                type="date"
                className="w-full border rounded-lg px-3 py-2 text-sm"
                onChange={(e) => {
                  onQuickAction?.(e.target.value)
                }}
              />
            </div>
          )
        }
        if (td.name === "number_input") {
          return (
            <div className="p-3 bg-white border rounded-xl">
              <p className="text-sm text-gray-600 mb-2">{td.question}</p>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={td.min}
                  max={td.max}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  onChange={(e) => {
                    onQuickAction?.(e.target.value)
                  }}
                />
                {td.unit && <span className="text-sm text-gray-500">{td.unit}</span>}
              </div>
            </div>
          )
        }
        return null
      })() : null}

      {/* Inline quick actions - clicking category buttons sends the text */}
      {/* [已屏蔽] 快捷问题类型
      {!message.streaming && !artifactType && onQuickAction && text.length > 30 ? (
        <QuickActions onSelect={onQuickAction} />
      ) : null}
      */}
    </div>
  )
}

// =============================================================================
// Sidebar Panel Component
// =============================================================================


// =============================================================================
// Loading Indicator
// =============================================================================

function LoadingDots() {
  return (
    <div className="flex justify-start">
      <div className="bg-white border rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
          <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
          <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Main Chat Page
// =============================================================================

// Generate UUID v4 (compatible with all browsers)
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

export default function ChatPage() {
  const { sessionId } = useParams()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [sessionState, setSessionState] = useState<SessionState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [streamingContent, setStreamingContent] = useState("")

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const [activeSessionId, setActiveSessionId] = useState(
    sessionId || generateUUID()
  )

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingContent, scrollToBottom])

  // Fetch session state
  useEffect(() => {
    if (!activeSessionId) return

    fetch(`/sessions/${activeSessionId}`)
      .then((r) => r.json())
      .then((data) => {
        if (data && data.current_step) {
          setSessionState(data)
        }
      })
      .catch(() => {})
  }, [activeSessionId])

  const handleQuickSelect = (text: string) => {
    setInput(text)
    inputRef.current?.focus()
  }

  const handleSendMessage = useCallback(async (content: string) => {
    if (!content.trim() || loading) return

    const userMessage: Message = {
      id: generateId(),
      role: "user",
      content,
    }

    setMessages((prev) => [...prev, userMessage])
    const userInput = content
    setInput("")
    setLoading(true)
    setError(null)
    setStreamingContent("")

    try {
      const res = await fetch("/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: userInput }],
          stream: true,
          sessionId: activeSessionId
        }),
        signal: AbortSignal.timeout(120000),
      })

      if (!res.ok) {
        throw new Error(`服务器响应错误: ${res.status} ${res.statusText}`)
      }

      const reader = res.body?.getReader()
      const decoder = new TextDecoder()

      if (reader) {
        // Create a streaming assistant message
        const streamingMessageId = generateId()
        setMessages((prev) => [
          ...prev,
          {
            id: streamingMessageId,
            role: "assistant",
            content: "",
            streaming: true,
          },
        ])

        let fullContent = ""
        let streamDone = false

        // Read loop with periodic yield to allow React renders
        const readNext = async (): Promise<void> => {
          const { done, value } = await reader.read()
          if (done) {
            streamDone = true
            return
          }

          const chunk = decoder.decode(value, { stream: true })

          for (const line of chunk.split("\n")) {
            if (!line.startsWith("data: ")) continue
            const dataStr = line.slice(6).trim()
            if (dataStr === "[DONE]") {
              streamDone = true
              return
            }

            try {
              const data = JSON.parse(dataStr)

              // OpenAI chunk format: choices[0].delta.content
              const content = data.choices?.[0]?.delta?.content
              const finishReason = data.choices?.[0]?.finish_reason

              if (content) {
                fullContent += content
                setStreamingContent(fullContent)
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === streamingMessageId
                      ? { ...msg, content: fullContent }
                      : msg
                  )
                )
              }

              if (finishReason === "stop") {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === streamingMessageId
                      ? { ...msg, streaming: false }
                      : msg
                  )
                )
              }
            } catch (parseErr) {
              console.error("解析流数据失败:", parseErr)
            }
          }

          // Yield to event loop periodically to keep UI responsive
          await new Promise(resolve => setTimeout(resolve, 0))
          if (!streamDone) {
            await readNext()
          }
        }

        await readNext()
      }

      // Update session state
      if (activeSessionId) {
        fetch(`/sessions/${activeSessionId}`)
          .then((r) => r.json())
          .then(setSessionState)
          .catch((stateErr) => {
            console.error("获取会话状态失败:", stateErr)
          })
      }
    } catch (err) {
      console.error("发送消息失败:", err)
      const errorMessage = err instanceof Error ? err.message : "网络连接失败，请检查后端服务是否正常运行"
      setError(errorMessage)

      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          role: "assistant",
          content: `抱歉，发送消息时出现错误：${errorMessage}`,
        },
      ])
    } finally {
      setLoading(false)
      setStreamingContent("")
      inputRef.current?.focus()
    }
  }, [activeSessionId, loading])

  const handleSendFile = useCallback(async (fileContent: string, filename: string) => {
    // Send file content as a user message
    const content = `[文件上传] ${filename}\n\n文件内容：\n${fileContent.slice(0, 1000)}${fileContent.length > 1000 ? "..." : ""}`
    await handleSendMessage(content)
  }, [handleSendMessage])

  const sendMessage = async () => {
    await handleSendMessage(input)
  }

  const currentStep = sessionState?.current_step || 1
  const completedSteps = sessionState?.completed_steps || []

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left: Chat Area (70%) */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header className={cn("px-4 py-3 flex items-center gap-3 shadow-sm", THEME.primary)}>
          <Link
            to="/"
            className="p-2 hover:bg-blue-700 rounded-lg transition-colors"
            aria-label="返回首页"
          >
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </Link>
          <div>
            <h1 className="font-semibold text-white">劳动争议智能咨询</h1>
            {sessionState && (
              <p className="text-xs text-blue-200">
                第{currentStep}步 · {sessionState.current_step_name}
              </p>
            )}
          </div>
        </header>

      {/* Step Progress */}
      {sessionState && (
        <div className="bg-white border-b border-gray-200">
          <StepIndicator
            currentStep={currentStep}
            completedSteps={completedSteps}
            onStepClick={() => {}}
          />
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="mx-4 mt-2 bg-red-50 border-l-4 border-red-500 px-4 py-3 rounded-r-lg">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <div className="ml-3 flex-1">
              <p className="text-sm text-red-700">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="ml-3 shrink-0 text-red-500 hover:text-red-700"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-16">
            <div className="text-5xl mb-4">⚖️</div>
            <h2 className="text-xl font-medium text-gray-600 mb-2">
              欢迎使用劳动争议智能咨询系统
            </h2>
            <p className="text-sm text-gray-500 mb-8 max-w-md mx-auto">
              请描述您的劳动争议问题，AI助手将引导您完成从咨询到文书生成的完整维权流程
            </p>

            <div className="text-left max-w-sm mx-auto">
              <p className="text-xs text-gray-400 mb-3 font-medium uppercase tracking-wide">
                常见问题类型
              </p>
              <div className="grid grid-cols-2 gap-2">
                {QUICK_CATEGORIES.map((cat) => (
                  <button
                    key={cat.label}
                    onClick={() => handleQuickSelect(`我想咨询${cat.label}问题`)}
                    className="flex items-center gap-2 bg-white hover:bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-700 border border-gray-200 shadow-sm transition-all hover:shadow"
                  >
                    <span>{cat.icon}</span>
                    <span>{cat.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              "flex",
              msg.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            <RichMessageRenderer message={msg} onQuickAction={handleQuickSelect} />
          </div>
        ))}

        {loading && !streamingContent && <LoadingDots />}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 bg-gradient-to-t from-gray-50 to-white p-4 shadow-[0_-4px_20px_rgba(0,0,0,0.04)]">
        <div className="flex gap-3 items-end max-w-3xl mx-auto">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                sendMessage()
              }
            }}
            placeholder="描述您的劳动争议问题..."
            rows={1}
            className="flex-1 border border-gray-200 rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent focus:shadow-[0_0_0_4px_rgba(59,130,246,0.12)] resize-none text-sm text-gray-800 placeholder-gray-400 bg-white transition-all duration-200"
            style={{ maxHeight: "120px" }}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className={cn(
              "flex-shrink-0 w-11 h-11 rounded-2xl flex items-center justify-center transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500",
              loading || !input.trim()
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700 hover:shadow-lg hover:shadow-blue-200 active:scale-95 active:bg-blue-800"
            )}
          >
            {loading ? (
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <svg className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </div>
        <p className="text-xs text-gray-400 text-center mt-2.5 font-medium tracking-wide">
          按 Enter 发送，Shift+Enter 换行
        </p>
      </div>
    </div>

    {/* Right: Info Panel (30%) */}
    <div className="w-[30%] min-w-[300px] max-w-[400px] border-l border-gray-200">
      <InfoPanel
        currentStep={currentStep}
        currentStepName={sessionState?.current_step_name || ""}
        sessionId={activeSessionId}
        caseCategory={sessionState?.case_category}
        qualification={sessionState?.qualification as InfoPanelProps["qualification"]}
        riskAssessment={sessionState?.risk_assessment as InfoPanelProps["riskAssessment"]}
        evidenceItems={sessionState?.evidence_items}
        documentDraft={sessionState?.document_draft as InfoPanelProps["documentDraft"]}
        onSendMessage={handleSendMessage}
        onSendFile={handleSendFile}
      />
    </div>
  </div>
  )
}
