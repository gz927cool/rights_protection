import React, { useState, useRef } from "react"

interface EvidenceItem {
  id: string
  name: string
  description: string
  category: string
  tier: number
  status: "" | "A" | "B" | "C"
  uploaded_file_refs: string[]
}

interface EvidenceFormProps {
  sessionId: string
  caseCategory: string
  evidenceItems: EvidenceItem[]
  onStatusChange: (itemId: string, status: string) => void
}

const tierLabels: Record<number, string> = {
  1: "必备证据",
  2: "加强证据",
  3: "兜底证据",
}

const tierColors: Record<number, string> = {
  1: "bg-red-50 border-red-200",
  2: "bg-yellow-50 border-yellow-200",
  3: "bg-blue-50 border-blue-200",
}

const statusConfig = {
  A: { label: "已有", color: "bg-green-100 text-green-800 border-green-300", hover: "hover:bg-green-200" },
  B: { label: "可补充", color: "bg-yellow-100 text-yellow-800 border-yellow-300", hover: "hover:bg-yellow-200" },
  C: { label: "无法获得", color: "bg-red-100 text-red-800 border-red-300", hover: "hover:bg-red-200" },
  "": { label: "未标记", color: "bg-gray-100 text-gray-600 border-gray-300", hover: "hover:bg-gray-200" },
}

function calculateCompleteness(items: EvidenceItem[]): { level: string; color: string; percent: number } {
  if (items.length === 0) return { level: "严重缺乏", color: "text-red-600", percent: 0 }

  const tier1Items = items.filter(i => i.tier === 1)
  const tier2Items = items.filter(i => i.tier === 2)
  const tier3Items = items.filter(i => i.tier === 3)

  const tier1Complete = tier1Items.filter(i => i.status === "A").length
  const tier2Complete = tier2Items.filter(i => i.status === "A" || i.status === "B").length
  const tier3Complete = tier3Items.filter(i => i.status === "A" || i.status === "B").length

  const tier1Ratio = tier1Items.length > 0 ? tier1Complete / tier1Items.length : 0
  const tier2Ratio = tier2Items.length > 0 ? tier2Complete / tier2Items.length : 0
  const tier3Ratio = tier3Items.length > 0 ? tier3Complete / tier3Items.length : 0

  const weighted = tier1Ratio * 0.5 + tier2Ratio * 0.3 + tier3Ratio * 0.2
  const percent = Math.round(weighted * 100)

  if (percent >= 80 && tier1Items.length > 0 && tier1Complete === tier1Items.length) {
    return { level: "充分", color: "text-green-600", percent }
  } else if (percent >= 50) {
    return { level: "基本完整", color: "text-yellow-600", percent }
  } else if (percent >= 20) {
    return { level: "不完整", color: "text-orange-500", percent }
  } else {
    return { level: "严重缺乏", color: "text-red-600", percent }
  }
}

export default function EvidenceForm({
  sessionId,
  caseCategory,
  evidenceItems: initialItems,
  onStatusChange,
}: EvidenceFormProps) {
  const [items, setItems] = useState<EvidenceItem[]>(initialItems)
  const [uploadingId, setUploadingId] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({})

  const completeness = calculateCompleteness(items)

  const groupedItems = {
    1: items.filter(i => i.tier === 1),
    2: items.filter(i => i.tier === 2),
    3: items.filter(i => i.tier === 3),
  }

  const handleStatusClick = (itemId: string, status: string) => {
    const newStatus = status === "A" ? "B" : status === "B" ? "C" : status === "C" ? "" : "A"
    setItems(prev => prev.map(item => item.id === itemId ? { ...item, status: newStatus as EvidenceItem["status"] } : item))
    onStatusChange(itemId, newStatus)
  }

  const handleUploadClick = (itemId: string) => {
    fileInputRefs.current[itemId]?.click()
  }

  const handleFileChange = async (itemId: string, event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setUploadingId(itemId)
    setUploadError(null)

    const formData = new FormData()
    formData.append("file", file)
    formData.append("evidence_item_id", itemId)

    try {
      const response = await fetch(`/upload/${sessionId}`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`上传失败: ${response.statusText}`)
      }

      const result = await response.json()
      setItems(prev => prev.map(item =>
        item.id === itemId
          ? { ...item, uploaded_file_refs: [...item.uploaded_file_refs, result.file_ref || file.name] }
          : item
      ))
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "上传失败")
    } finally {
      setUploadingId(null)
      if (fileInputRefs.current[itemId]) {
        fileInputRefs.current[itemId].value = ""
      }
    }
  }

  return (
    <div className="w-full max-w-6xl mx-auto p-4">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">证据收集</h2>
        <p className="text-gray-600 mb-4">案件类型: {caseCategory}</p>

        {/* Completeness Rating */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-lg font-semibold text-gray-700">证据完整度</span>
            <span className={`text-lg font-bold ${completeness.color}`}>
              {completeness.level} ({completeness.percent}%)
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all duration-300 ${
                completeness.percent >= 80 ? "bg-green-500" :
                completeness.percent >= 50 ? "bg-yellow-500" :
                completeness.percent >= 20 ? "bg-orange-500" : "bg-red-500"
              }`}
              style={{ width: `${completeness.percent}%` }}
            />
          </div>
          <div className="mt-2 text-sm text-gray-500">
            已有 {items.filter(i => i.status === "A").length} 项 / 可补充 {items.filter(i => i.status === "B").length} 项 / 无法获得 {items.filter(i => i.status === "C").length} 项
          </div>
        </div>

        {uploadError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {uploadError}
          </div>
        )}
      </div>

      {/* 3-Column Grid for Tiers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map(tier => (
          <div
            key={tier}
            className={`rounded-lg border p-4 ${tierColors[tier as 1|2|3]}`}
          >
            <h3 className="text-lg font-bold text-gray-800 mb-4 pb-2 border-b border-gray-300">
              {tierLabels[tier as 1|2|3]}
              <span className="ml-2 text-sm font-normal text-gray-600">
                ({groupedItems[tier as 1|2|3].length}项)
              </span>
            </h3>

            <div className="space-y-3">
              {groupedItems[tier as 1|2|3].map((item: EvidenceItem) => {
                const statusKey = (item.status || "") as "A" | "B" | "C" | ""
                const status = statusConfig[statusKey]
                const isUploading = uploadingId === item.id

                return (
                  <div
                    key={item.id}
                    className="bg-white rounded-lg border border-gray-200 p-3 shadow-sm"
                  >
                    {/* Item Header */}
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-800 text-sm">{item.name}</h4>
                        <p className="text-xs text-gray-500 mt-1">{item.description}</p>
                      </div>
                    </div>

                    {/* Status Buttons */}
                    <div className="flex flex-wrap gap-1 mt-3">
                      {(["A", "B", "C"] as const).map(s => {
                        const cfg = statusConfig[s]
                        const isActive = item.status === s
                        return (
                          <button
                            key={s}
                            onClick={() => handleStatusClick(item.id, s)}
                            className={`px-2 py-1 text-xs rounded border transition-colors ${
                              isActive
                                ? cfg.color
                                : `bg-white text-gray-600 border-gray-300 ${cfg.hover}`
                            }`}
                          >
                            {s === "A" ? "已有" : s === "B" ? "可补充" : "无法获得"}
                          </button>
                        )
                      })}
                      <span className={`ml-auto px-2 py-1 text-xs rounded border ${status.color}`}>
                        {status.label}
                      </span>
                    </div>

                    {/* Upload Section */}
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500">
                          {item.uploaded_file_refs.length > 0
                            ? `已上传 ${item.uploaded_file_refs.length} 个文件`
                            : "未上传文件"}
                        </span>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleUploadClick(item.id)}
                            disabled={isUploading}
                            className={`px-3 py-1 text-xs rounded border transition-colors ${
                              isUploading
                                ? "bg-gray-100 text-gray-400 border-gray-300 cursor-not-allowed"
                                : "bg-blue-50 text-blue-700 border-blue-300 hover:bg-blue-100"
                            }`}
                          >
                            {isUploading ? "上传中..." : "上传"}
                          </button>
                        </div>
                      </div>
                      <input
                        ref={el => { fileInputRefs.current[item.id] = el as HTMLInputElement }}
                        type="file"
                        className="hidden"
                        onChange={e => handleFileChange(item.id, e)}
                        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                      />
                      {item.uploaded_file_refs.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {item.uploaded_file_refs.map((ref, idx) => (
                            <div key={idx} className="text-xs text-gray-600 flex items-center gap-1">
                              <span className="w-2 h-2 bg-green-500 rounded-full" />
                              {ref}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">状态说明</h4>
        <div className="flex flex-wrap gap-4 text-xs text-gray-600">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-green-100 border border-green-300 rounded" />
            A - 已有 (证据已掌握)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-yellow-100 border border-yellow-300 rounded" />
            B - 可补充 (可通过补充获取)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-red-100 border border-red-300 rounded" />
            C - 无法获得 (客观原因无法获取)
          </span>
        </div>
      </div>
    </div>
  )
}
