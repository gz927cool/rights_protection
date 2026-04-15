import { useState } from 'react'

export interface DocumentDraft {
  template_type: string
  content: string
  gaps: string[]
  created_at: string
  updated_at: string
}

export interface RightsItem {
  right_name: string
  amount: number
  calculation_basis: string
}

interface DocumentPreviewProps {
  document: DocumentDraft | null
  rightsList: RightsItem[]
  onRegenerate?: () => void
}

function formatDatetime(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function DocumentTypeLabel({ templateType }: { templateType: string }) {
  const labels: Record<string, string> = {
    arbitration: '仲裁申请书',
    mediation: '调解申请书',
    仲裁申请书: '仲裁申请书',
    调解申请书: '调解申请书',
  }
  const label = labels[templateType] ?? templateType ?? '文书预览'
  return (
    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-50 text-blue-700 border border-blue-200">
      {label}
    </span>
  )
}

export default function DocumentPreview({
  document,
  rightsList,
  onRegenerate,
}: DocumentPreviewProps) {
  const [alertMsg, setAlertMsg] = useState<string | null>(null)

  function showAlert(msg: string) {
    setAlertMsg(msg)
    setTimeout(() => setAlertMsg(null), 2500)
  }

  if (!document) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <svg
          className="w-12 h-12 mb-3"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p className="text-sm">暂无文书内容</p>
      </div>
    )
  }

  const totalAmount = rightsList.reduce((sum, r) => sum + (r.amount ?? 0), 0)

  return (
    <div className="flex flex-col h-full">
      {/* Alert banner */}
      {alertMsg && (
        <div className="mb-4 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm animate-pulse">
          {alertMsg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <DocumentTypeLabel templateType={document.template_type} />
          <span className="text-xs text-gray-400">
            {formatDatetime(document.updated_at || document.created_at)}
          </span>
        </div>
        <button
          onClick={onRegenerate}
          className="px-4 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-gray-600"
        >
          重新生成
        </button>
      </div>

      {/* Two-column layout */}
      <div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0">

        {/* Document content */}
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-700">文书内容</h3>
            <button
              onClick={() => showAlert('复制功能开发中')}
              className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              复制
            </button>
          </div>
          <div className="flex-1 overflow-y-auto bg-white border border-gray-200 rounded-xl p-5">
            <pre className="whitespace-pre-wrap break-words text-sm text-gray-800 leading-relaxed font-mono">
              {document.content || '（暂无内容）'}
            </pre>
          </div>
        </div>

        {/* Right sidebar: gaps + rights */}
        <div className="w-full lg:w-72 flex flex-col gap-4">

          {/* Gaps panel */}
          {document.gaps && document.gaps.length > 0 && (
            <div className="flex flex-col">
              <h3 className="text-sm font-semibold text-red-600 mb-2 flex items-center gap-1.5">
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                待补全字段
                <span className="ml-auto text-xs font-normal text-gray-400">
                  {document.gaps.length} 项
                </span>
              </h3>
              <div className="bg-red-50 border border-red-100 rounded-xl p-3 space-y-1.5">
                {document.gaps.map((gap, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-red-700">
                    <span className="mt-0.5 shrink-0 text-red-400">•</span>
                    <span>{gap}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Rights summary */}
          {rightsList.length > 0 && (
            <div className="flex flex-col">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">权益清单</h3>
              <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-3 py-2 text-left font-medium text-gray-600">权益项目</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-600">金额</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {rightsList.map((item, i) => (
                      <tr key={i} className="hover:bg-gray-50 transition-colors">
                        <td className="px-3 py-2 text-gray-700">{item.right_name}</td>
                        <td className="px-3 py-2 text-right text-gray-800 font-medium">
                          ¥{item.amount.toLocaleString('zh-CN')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="bg-blue-50">
                      <td className="px-3 py-2 text-sm font-semibold text-blue-700">合计</td>
                      <td className="px-3 py-2 text-right text-sm font-bold text-blue-700">
                        ¥{totalAmount.toLocaleString('zh-CN')}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
              {document.gaps && document.gaps.length > 0 && (
                <p className="mt-1.5 text-xs text-amber-600">
                  * 补充缺失信息后可重新计算准确金额
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-3 mt-4 pt-4 border-t border-gray-100">
        <button
          onClick={onRegenerate}
          className="px-4 py-2 text-sm border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 transition-colors font-medium"
        >
          修改文书
        </button>
        <button
          onClick={() => showAlert('导出功能开发中')}
          className="px-4 py-2 text-sm border border-gray-300 text-gray-400 rounded-lg cursor-not-allowed opacity-60"
          disabled
        >
          导出Word
        </button>
        <button
          onClick={() => showAlert('导出功能开发中')}
          className="px-4 py-2 text-sm border border-gray-300 text-gray-400 rounded-lg cursor-not-allowed opacity-60"
          disabled
        >
          导出PDF
        </button>
      </div>
    </div>
  )
}
