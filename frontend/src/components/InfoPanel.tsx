import React, { useState, useRef } from "react"

export interface InfoPanelProps {
  currentStep: number
  currentStepName: string
  sessionId: string
  caseCategory?: string
  qualification?: {
    case_types?: string[]
    rights_list?: Array<{ right_name: string; amount: number; calculation_basis: string; legal_basis: string }>
  }
  riskAssessment?: {
    level?: string
    risk_points?: Array<{ risk_type: string; description: string; is_high_risk: boolean; mitigation: string }>
  }
  evidenceItems?: Array<{
    id: string
    name: string
    description: string
    tier: number
    status: "" | "A" | "B" | "C"
    uploaded_file_refs: string[]
  }>
  documentDraft?: {
    template_type?: string
    content?: string
    gaps?: string[]
    created_at?: string
    updated_at?: string
  }
  onSendMessage: (content: string) => void
  onSendFile: (fileContent: string, filename: string) => void
}

// ============================================================================
// Step 2: Case Category Confirmation Card
// ============================================================================
function Step2Info({ caseCategory }: { caseCategory?: string }) {
  const categories = [
    { label: "欠薪/克扣工资", icon: "💰", color: "from-red-50 to-orange-50", border: "border-red-200" },
    { label: "被辞退/开除", icon: "🚫", color: "from-orange-50 to-amber-50", border: "border-orange-200" },
    { label: "工伤认定", icon: "🏥", color: "from-blue-50 to-cyan-50", border: "border-blue-200" },
    { label: "调岗降薪", icon: "📉", color: "from-purple-50 to-violet-50", border: "border-purple-200" },
    { label: "社保欠缴", icon: "🏦", color: "from-emerald-50 to-teal-50", border: "border-emerald-200" },
    { label: "其他争议", icon: "❓", color: "from-gray-50 to-slate-50", border: "border-gray-300" },
  ]

  const selectedCat = categories.find(c =>
    caseCategory && caseCategory.includes(c.label.split("/")[0].trim())
  ) || categories[5]

  return (
    <div className="space-y-3">
      <div className={`p-4 rounded-xl border-2 ${selectedCat.border} bg-gradient-to-br ${selectedCat.color}`}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">{selectedCat.icon}</span>
          <span className="font-semibold text-gray-800">
            {caseCategory ? `案件类型：${caseCategory}` : "案件类型待确认"}
          </span>
        </div>
        <p className="text-sm text-gray-600">
          {caseCategory
            ? "AI正在分析您的案件情况，请继续描述详细情形"
            : "请在聊天中描述您遇到的劳动争议类型"}
        </p>
      </div>

      <div className="bg-gray-50 rounded-xl p-3">
        <p className="text-xs text-gray-500 mb-2 font-medium">可选案件类型：</p>
        <div className="flex flex-wrap gap-1.5">
          {categories.slice(0, 5).map(cat => (
            <span
              key={cat.label}
              className={`text-xs px-2 py-1 rounded-full border ${
                caseCategory && cat.label.includes(caseCategory.split("/")[0])
                  ? "bg-blue-100 border-blue-300 text-blue-700"
                  : "bg-white border-gray-200 text-gray-600"
              }`}
            >
              {cat.icon} {cat.label.split("/")[0]}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Step 3: Common Questions Form
// ============================================================================
function Step3Form({
  onSend,
}: {
  onSend: (content: string) => void
}) {
  const [formData, setFormData] = useState({
    employment_status: "",
    contract_status: "",
    monthly_salary: "",
    salary_payment_method: "",
    social_security: "",
    job_position: "",
    entry_date: "",
    amount_involved: "",
    expected_result: "",
  })

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSend = () => {
    const lines = [
      "【基本信息】",
      `就业状态：${formData.employment_status || "未填写"}`,
      `劳动合同签订情况：${formData.contract_status || "未填写"}`,
      `工作岗位：${formData.job_position || "未填写"}`,
      `入职时间：${formData.entry_date || "未填写"}`,
      `月工资：${formData.monthly_salary || "未填写"}元`,
      `工资发放方式：${formData.salary_payment_method || "未填写"}`,
      `社保缴纳情况：${formData.social_security || "未填写"}`,
      `涉及金额：${formData.amount_involved || "未填写"}元`,
      `期望结果：${formData.expected_result || "未填写"}`,
    ]
    onSend(lines.join("\n"))
  }

  const isComplete = formData.employment_status && formData.monthly_salary

  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-500">请填写以下信息（选填，但填写详细可获得更准确的分析）：</p>

      {/* Employment Status */}
      <div>
        <label className="text-xs font-medium text-gray-700 mb-1 block">就业状态 *</label>
        <div className="flex gap-1.5 flex-wrap">
          {["在职", "离职", "待岗"].map(opt => (
            <button
              key={opt}
              onClick={() => handleChange("employment_status", opt)}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                formData.employment_status === opt
                  ? "bg-blue-100 border-blue-400 text-blue-700"
                  : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      {/* Contract Status */}
      <div>
        <label className="text-xs font-medium text-gray-700 mb-1 block">劳动合同签订情况</label>
        <div className="flex gap-1.5 flex-wrap">
          {["已签订", "未签订", "不清楚"].map(opt => (
            <button
              key={opt}
              onClick={() => handleChange("contract_status", opt)}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                formData.contract_status === opt
                  ? "bg-blue-100 border-blue-400 text-blue-700"
                  : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      {/* Job Position */}
      <div>
        <label className="text-xs font-medium text-gray-700 mb-1 block">工作岗位</label>
        <input
          type="text"
          value={formData.job_position}
          onChange={e => handleChange("job_position", e.target.value)}
          placeholder="如：外卖骑手、程序员"
          className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      {/* Entry Date */}
      <div>
        <label className="text-xs font-medium text-gray-700 mb-1 block">入职时间</label>
        <input
          type="date"
          value={formData.entry_date}
          onChange={e => handleChange("entry_date", e.target.value)}
          className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      {/* Monthly Salary */}
      <div>
        <label className="text-xs font-medium text-gray-700 mb-1 block">月工资（元） *</label>
        <input
          type="number"
          value={formData.monthly_salary}
          onChange={e => handleChange("monthly_salary", e.target.value)}
          placeholder="如：8000"
          className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      {/* Salary Payment Method */}
      <div>
        <label className="text-xs font-medium text-gray-700 mb-1 block">工资发放方式</label>
        <select
          value={formData.salary_payment_method}
          onChange={e => handleChange("salary_payment_method", e.target.value)}
          className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
        >
          <option value="">请选择</option>
          <option value="银行转账">银行转账</option>
          <option value="现金">现金</option>
          <option value="微信/支付宝">微信/支付宝</option>
          <option value="混合方式">混合方式</option>
        </select>
      </div>

      {/* Social Security */}
      <div>
        <label className="text-xs font-medium text-gray-700 mb-1 block">社保缴纳情况</label>
        <select
          value={formData.social_security}
          onChange={e => handleChange("social_security", e.target.value)}
          className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
        >
          <option value="">请选择</option>
          <option value="正常缴纳">正常缴纳</option>
          <option value="部分缴纳">部分缴纳</option>
          <option value="未缴纳">未缴纳</option>
          <option value="不清楚">不清楚</option>
        </select>
      </div>

      {/* Amount Involved */}
      <div>
        <label className="text-xs font-medium text-gray-700 mb-1 block">涉及金额（元）</label>
        <input
          type="number"
          value={formData.amount_involved}
          onChange={e => handleChange("amount_involved", e.target.value)}
          placeholder="如：24000"
          className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      {/* Expected Result */}
      <div>
        <label className="text-xs font-medium text-gray-700 mb-1 block">期望结果</label>
        <textarea
          value={formData.expected_result}
          onChange={e => handleChange("expected_result", e.target.value)}
          placeholder="如：拿回被欠工资和赔偿金"
          rows={2}
          className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
        />
      </div>

      {/* Send Button */}
      <button
        onClick={handleSend}
        disabled={!isComplete}
        className={`w-full py-2.5 rounded-xl text-sm font-medium transition-all ${
          isComplete
            ? "bg-blue-600 text-white hover:bg-blue-700 shadow-sm"
            : "bg-gray-100 text-gray-400 cursor-not-allowed"
        }`}
      >
        发送信息给AI
      </button>
      {!isComplete && (
        <p className="text-xs text-gray-400 text-center">* 请至少填写就业状态和月工资</p>
      )}
    </div>
  )
}

// ============================================================================
// Step 4: Case Type Display
// ============================================================================
function Step4Info({ caseCategory }: { caseCategory?: string }) {
  return (
    <div className="space-y-3">
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-3">
        <p className="text-xs text-blue-600 mb-1 font-medium">当前案由</p>
        <p className="font-semibold text-gray-800">{caseCategory || "待确定"}</p>
      </div>

      <div className="bg-gray-50 rounded-xl p-3">
        <p className="text-xs text-gray-500 mb-2 font-medium">特殊问题说明</p>
        <p className="text-xs text-gray-600">
          AI正在根据您的案件类型，追问确定三级案由。请在聊天中回复相关问题。
        </p>
      </div>

      <div className="border border-gray-200 rounded-xl p-3">
        <p className="text-xs font-medium text-gray-700 mb-2">案由体系</p>
        <div className="space-y-1.5 text-xs">
          <div className="flex items-start gap-2">
            <span className="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded text-xs">一级</span>
            <span className="text-gray-600">{caseCategory || "待确定"}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded text-xs">二级</span>
            <span className="text-gray-400 italic">AI追问后确定</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded text-xs">三级</span>
            <span className="text-gray-400 italic">AI追问后确定</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Step 5: Rights Summary
// ============================================================================
function Step5Info({
  qualification,
  caseCategory,
}: {
  qualification?: InfoPanelProps["qualification"]
  caseCategory?: string
}) {
  const rights = qualification?.rights_list || []

  if (rights.length === 0) {
    return (
      <div className="space-y-3">
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-center">
          <p className="text-2xl mb-2">⚖️</p>
          <p className="text-sm text-gray-600">AI正在分析案件，准备生成权益清单...</p>
        </div>
        <div className="bg-gray-50 rounded-xl p-3">
          <p className="text-xs text-gray-500 font-medium mb-1">案件类型</p>
          <p className="text-sm text-gray-700">{caseCategory || "待确定"}</p>
        </div>
      </div>
    )
  }

  const total = rights.reduce((sum, r) => sum + (r.amount || 0), 0)

  return (
    <div className="space-y-3">
      <div className="bg-gradient-to-br from-blue-50 to-emerald-50 border border-blue-200 rounded-xl p-3">
        <p className="text-xs text-blue-600 mb-1 font-medium">案件定性</p>
        <p className="font-semibold text-gray-800">
          {qualification?.case_types?.join(" > ") || caseCategory}
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="bg-gray-50 px-3 py-2 border-b border-gray-200">
          <p className="text-xs font-semibold text-gray-700">权益清单</p>
        </div>
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-3 py-1.5 text-left text-gray-600 font-medium">权益项目</th>
              <th className="px-3 py-1.5 text-right text-gray-600 font-medium">金额</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rights.map((r, i) => (
              <tr key={i}>
                <td className="px-3 py-2 text-gray-700">{r.right_name}</td>
                <td className="px-3 py-2 text-right font-medium text-gray-800">
                  ¥{(r.amount || 0).toLocaleString("zh-CN")}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="bg-blue-50">
              <td className="px-3 py-2 font-semibold text-blue-700">合计</td>
              <td className="px-3 py-2 text-right font-bold text-blue-700">
                ¥{total.toLocaleString("zh-CN")}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

// ============================================================================
// Step 6: Evidence Checklist with Upload
// ============================================================================
function Step6Evidence({
  evidenceItems = [],
  onSendMessage,
  onSendFile,
}: {
  evidenceItems: InfoPanelProps["evidenceItems"]
  onSendMessage: (content: string) => void
  onSendFile: (fileContent: string, filename: string) => void
}) {
  const [uploadingId, setUploadingId] = useState<string | null>(null)
  const [pendingFiles, setPendingFiles] = useState<Record<string, { name: string; content: string }>>({})
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({})

  const grouped = {
    1: evidenceItems.filter(e => e.tier === 1),
    2: evidenceItems.filter(e => e.tier === 2),
    3: evidenceItems.filter(e => e.tier === 3),
  }

  const tierLabels = { 1: "必备证据", 2: "加强证据", 3: "兜底证据" }
  const tierColors = {
    1: "bg-red-50 border-red-200",
    2: "bg-yellow-50 border-yellow-200",
    3: "bg-blue-50 border-blue-200",
  }

  const handleFileSelect = async (itemId: string, event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setUploadingId(itemId)

    try {
      const content = await file.text()
      setPendingFiles(prev => ({ ...prev, [itemId]: { name: file.name, content } }))
    } catch {
      alert("文件读取失败")
    } finally {
      setUploadingId(null)
      if (fileInputRefs.current[itemId]) {
        fileInputRefs.current[itemId]!.value = ""
      }
    }
  }

  const handleUploadAndSend = async (itemId: string) => {
    const file = pendingFiles[itemId]
    if (!file) return

    // Send file content as a message to the agent
    const msg = `[文件上传] ${file.name}\n\n文件内容：\n${file.content.slice(0, 500)}${file.content.length > 500 ? "..." : ""}`
    onSendFile(file.content, file.name)
    onSendMessage(msg)

    setPendingFiles(prev => {
      const next = { ...prev }
      delete next[itemId]
      return next
    })
  }

  const totalEvidence = evidenceItems.length
  const hasA = evidenceItems.filter(e => e.status === "A").length
  const hasB = evidenceItems.filter(e => e.status === "B").length
  const hasC = evidenceItems.filter(e => e.status === "C").length

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="bg-gray-50 rounded-xl p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-gray-700">证据状态</span>
          <span className="text-xs text-gray-500">
            A={hasA} / B={hasB} / C={hasC} / 合计={totalEvidence}
          </span>
        </div>
        <div className="text-xs text-gray-500 space-x-2">
          <span className="text-green-600">● A=已有</span>
          <span className="text-yellow-600">● B=可补充</span>
          <span className="text-red-600">● C=无法获得</span>
        </div>
      </div>

      {/* Evidence Groups */}
      {([1, 2, 3] as const).map(tier => (
        <div key={tier} className={`rounded-xl border p-3 ${tierColors[tier]}`}>
          <p className="text-xs font-semibold text-gray-700 mb-2">
            {tierLabels[tier]}（{grouped[tier].length}项）
          </p>
          <div className="space-y-2">
            {grouped[tier].map(item => {
              const pending = pendingFiles[item.id]
              return (
                <div key={item.id} className="bg-white rounded-lg border border-gray-200 p-2">
                  <div className="flex items-start justify-between gap-1.5">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-800 truncate">{item.name}</p>
                      <p className="text-xs text-gray-400 truncate">{item.description}</p>
                    </div>
                    <span
                      className={`shrink-0 px-1.5 py-0.5 text-xs rounded border ${
                        item.status === "A"
                          ? "bg-green-100 text-green-700 border-green-300"
                          : item.status === "B"
                          ? "bg-yellow-100 text-yellow-700 border-yellow-300"
                          : item.status === "C"
                          ? "bg-red-100 text-red-700 border-red-300"
                          : "bg-gray-100 text-gray-500 border-gray-300"
                      }`}
                    >
                      {item.status || "未标记"}
                    </span>
                  </div>

                  {/* Upload section */}
                  <div className="mt-2 flex items-center gap-1.5">
                    <button
                      onClick={() => fileInputRefs.current[item.id]?.click()}
                      disabled={uploadingId === item.id}
                      className="px-2 py-1 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition-colors disabled:opacity-50"
                    >
                      {uploadingId === item.id ? "读取中..." : "选择文件"}
                    </button>
                    <input
                      ref={el => { fileInputRefs.current[item.id] = el }}
                      type="file"
                      className="hidden"
                      onChange={e => handleFileSelect(item.id, e)}
                      accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.txt"
                    />

                    {item.uploaded_file_refs.length > 0 && (
                      <span className="text-xs text-green-600 truncate">
                        ✓ {item.uploaded_file_refs[0]}
                      </span>
                    )}
                  </div>

                  {pending && (
                    <div className="mt-2 flex items-center gap-1.5">
                      <span className="text-xs text-gray-600 truncate flex-1">{pending.name}</span>
                      <button
                        onClick={() => handleUploadAndSend(item.id)}
                        className="px-2 py-1 text-xs bg-emerald-500 text-white rounded hover:bg-emerald-600 transition-colors"
                      >
                        发送
                      </button>
                      <button
                        onClick={() => setPendingFiles(prev => {
                          const next = { ...prev }
                          delete next[item.id]
                          return next
                        })}
                        className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700"
                      >
                        ✕
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}

      {totalEvidence === 0 && (
        <div className="text-center py-6 text-gray-400">
          <p className="text-2xl mb-2">📋</p>
          <p className="text-xs">AI正在加载证据清单...</p>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Step 7: Risk Assessment
// ============================================================================
function Step7Risk({ riskAssessment }: { riskAssessment?: InfoPanelProps["riskAssessment"] }) {
  if (!riskAssessment) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-center">
        <p className="text-2xl mb-2">⚠️</p>
        <p className="text-sm text-gray-600">AI正在评估风险...</p>
      </div>
    )
  }

  const levelColors = {
    高: { bg: "bg-red-50", border: "border-red-300", text: "text-red-700", badge: "bg-red-100 text-red-700" },
    中: { bg: "bg-amber-50", border: "border-amber-300", text: "text-amber-700", badge: "bg-amber-100 text-amber-700" },
    低: { bg: "bg-green-50", border: "border-green-300", text: "text-green-700", badge: "bg-green-100 text-green-700" },
  }
  const style = levelColors[riskAssessment.level as keyof typeof levelColors] || levelColors.中

  return (
    <div className="space-y-3">
      {/* Level Badge */}
      <div className={`${style.bg} border ${style.border} rounded-xl p-4 text-center`}>
        <p className="text-xs mb-1">风险等级</p>
        <p className={`text-2xl font-bold ${style.text}`}>{riskAssessment.level || "中"}</p>
      </div>

      {/* Risk Points */}
      {riskAssessment.risk_points && riskAssessment.risk_points.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-700">风险详情</p>
          {riskAssessment.risk_points.map((rp, i) => (
            <div
              key={i}
              className={`rounded-lg border p-3 ${
                rp.is_high_risk ? "bg-red-50 border-red-200" : "bg-yellow-50 border-yellow-200"
              }`}
            >
              <div className="flex items-start gap-2">
                <span className="text-lg">{rp.is_high_risk ? "⚠️" : "⚡"}</span>
                <div className="flex-1">
                  <p className="text-xs font-medium text-gray-800">{rp.risk_type}</p>
                  <p className="text-xs text-gray-600 mt-0.5">{rp.description}</p>
                  {rp.mitigation && (
                    <p className="text-xs text-blue-600 mt-1">建议：{rp.mitigation}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Step 8: Document Preview
// ============================================================================
function Step8Documents({
  documentDraft,
}: {
  documentDraft?: InfoPanelProps["documentDraft"]
}) {
  if (!documentDraft) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-center">
        <p className="text-2xl mb-2">📄</p>
        <p className="text-sm text-gray-600">AI正在生成文书...</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="bg-gray-50 px-3 py-2 border-b border-gray-200 flex items-center justify-between">
          <span className="text-xs font-medium text-gray-700">
            {documentDraft.template_type === "arbitration" ? "仲裁申请书" : "文书草稿"}
          </span>
          <span className="text-xs text-gray-400">
            {documentDraft.updated_at
              ? new Date(documentDraft.updated_at).toLocaleDateString("zh-CN")
              : ""}
          </span>
        </div>
        <div className="p-3 max-h-64 overflow-y-auto">
          <pre className="whitespace-pre-wrap text-xs text-gray-700 font-mono leading-relaxed">
            {documentDraft.content?.slice(0, 800) || "（暂无内容）"}
            {(documentDraft.content?.length || 0) > 800 && "..."}
          </pre>
        </div>
      </div>

      {documentDraft.gaps && documentDraft.gaps.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3">
          <p className="text-xs font-medium text-red-700 mb-1">待补全字段</p>
          <div className="space-y-0.5">
            {documentDraft.gaps.map((gap, i) => (
              <p key={i} className="text-xs text-red-600">• {gap}</p>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Step 9: Roadmap
// ============================================================================
function Step9Roadmap({ caseCategory }: { caseCategory?: string }) {
  const steps = [
    { name: "协商", icon: "1", color: "bg-blue-500", desc: "与用人单位直接沟通" },
    { name: "调解", icon: "2", color: "bg-orange-500", desc: "申请工会/街道调解" },
    { name: "仲裁", icon: "3", color: "bg-red-500", desc: "向仲裁委申请仲裁" },
  ]

  return (
    <div className="space-y-3">
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-3">
        <p className="text-xs text-blue-600 mb-1 font-medium">推荐路径</p>
        <p className="text-sm font-semibold text-gray-800">
          {caseCategory?.includes("欠薪") || caseCategory?.includes("工伤")
            ? "调解 → 仲裁"
            : "协商 → 调解"}
        </p>
      </div>

      <div className="space-y-2">
        {steps.map(step => (
          <div
            key={step.name}
            className="flex items-center gap-3 bg-white border border-gray-200 rounded-xl p-3"
          >
            <div className={`w-8 h-8 rounded-full ${step.color} flex items-center justify-center text-white font-bold text-sm`}>
              {step.icon}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-800">{step.name}</p>
              <p className="text-xs text-gray-500">{step.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="text-center text-xs text-gray-400 py-2">
        协商 → 调解 → 仲裁
      </div>
    </div>
  )
}

// ============================================================================
// Step 10: Review & Lawyer Help
// ============================================================================
function Step10Review({
  onSend,
}: {
  onSend: (content: string) => void
}) {
  const templates = [
    "证据检查：证据清单是否充分？",
    "金额计算：赔偿金额计算对吗？",
    "胜算评估：仲裁胜算多大？",
    "策略咨询：先协商还是直接仲裁？",
    "文书检查：申请书有没有问题？",
  ]

  return (
    <div className="space-y-3">
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-center">
        <p className="text-2xl mb-1">🆘</p>
        <p className="text-sm font-medium text-emerald-800">需要人工复核？</p>
        <p className="text-xs text-emerald-600 mt-1">AI复核或一键求助工会律师</p>
      </div>

      <div>
        <p className="text-xs font-medium text-gray-700 mb-2">快捷复核模板</p>
        <div className="space-y-1.5">
          {templates.map((t, i) => (
            <button
              key={i}
              onClick={() => onSend(t)}
              className="w-full text-left px-3 py-2 bg-white border border-gray-200 rounded-lg text-xs text-gray-700 hover:bg-blue-50 hover:border-blue-200 transition-colors"
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={() => onSend("[一键求助律师] 请求工会律师复核我的案件")}
        className="w-full py-2.5 bg-emerald-600 text-white rounded-xl text-sm font-medium hover:bg-emerald-700 transition-colors"
      >
        📮 一键求助律师
      </button>

      <p className="text-xs text-gray-400 text-center">
        律师将在1-3个工作日内回复
      </p>
    </div>
  )
}

// ============================================================================
// Main InfoPanel Component
// ============================================================================
export default function InfoPanel({
  currentStep,
  currentStepName,
  sessionId: _sessionId,
  caseCategory,
  qualification,
  riskAssessment,
  evidenceItems,
  documentDraft,
  onSendMessage,
  onSendFile,
}: InfoPanelProps) {
  const stepTitles: Record<number, string> = {
    2: "问题初判",
    3: "通用问题",
    4: "特殊问题",
    5: "案件定性",
    6: "证据攻略",
    7: "风险提示",
    8: "文书生成",
    9: "行动路线图",
    10: "求助复核",
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="px-4 py-3 bg-white border-b border-gray-200 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-blue-500" />
          <span className="text-sm font-semibold text-gray-800">
            {currentStepName || stepTitles[currentStep] || "信息面板"}
          </span>
          <span className="ml-auto text-xs text-gray-400">
            第{currentStep}步
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {currentStep === 2 && <Step2Info caseCategory={caseCategory} />}
        {currentStep === 3 && <Step3Form onSend={onSendMessage} />}
        {currentStep === 4 && <Step4Info caseCategory={caseCategory} />}
        {currentStep === 5 && <Step5Info qualification={qualification} caseCategory={caseCategory} />}
        {currentStep === 6 && (
          <Step6Evidence
            evidenceItems={evidenceItems}
            onSendMessage={onSendMessage}
            onSendFile={onSendFile}
          />
        )}
        {currentStep === 7 && <Step7Risk riskAssessment={riskAssessment} />}
        {currentStep === 8 && <Step8Documents documentDraft={documentDraft} />}
        {currentStep === 9 && <Step9Roadmap caseCategory={caseCategory} />}
        {currentStep === 10 && <Step10Review onSend={onSendMessage} />}

        {currentStep < 2 && (
          <div className="space-y-4">
            <div className="bg-gradient-to-br from-blue-50 to-emerald-50 border border-blue-200 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-3xl">⚖️</span>
                <div>
                  <h3 className="font-semibold text-gray-800">劳动争议智能咨询系统</h3>
                  <p className="text-xs text-gray-500">您的AI法律助手</p>
                </div>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">
                本系统协助劳动者完整维护自身合法权益，覆盖从咨询、证据收集、风险评估到文书生成的完整维权流程。
              </p>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium text-gray-700">我可以帮您：</p>
              {[
                { icon: "💬", text: "分析您的劳动争议类型" },
                { icon: "📋", text: "梳理应得权益和赔偿金额" },
                { icon: "📎", text: "指导收集和整理证据材料" },
                { icon: "⚠️", text: "提示维权过程中的风险点" },
                { icon: "📄", text: "生成仲裁/调解申请书草稿" },
                { icon: "🗺️", text: "规划协商→调解→仲裁路线" },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-gray-600">
                  <span>{item.icon}</span>
                  <span>{item.text}</span>
                </div>
              ))}
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
              <p className="text-xs text-amber-800">
                <span className="font-medium">温馨提示：</span>
                本系统仅供参考，具体法律行动建议咨询专业律师。
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
