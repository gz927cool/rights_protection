import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { documents as documentsApi } from '../../services/api'

interface DocumentPreviewProps {
  caseId: string
}

export function DocumentPreview({ caseId }: DocumentPreviewProps) {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null)

  const { data: documents } = useQuery({
    queryKey: ['documents', caseId],
    queryFn: () => documentsApi.list(caseId).then(res => res.data),
    enabled: !!caseId
  })

  const handleExport = async (docId: string, format: 'docx' | 'pdf') => {
    try {
      const response = await documentsApi.export(docId, format)
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = `document.${format}`
      link.click()
    } catch (error) {
      console.error('Export failed:', error)
    }
  }

  const selectedDocument = documents?.find((d: { id: string }) => d.id === selectedDoc)

  return (
    <div className="document-preview">
      <div className="document-sidebar">
        <h3>文书列表</h3>
        {documents?.map((doc: { id: string; type: string }) => (
          <button
            key={doc.id}
            className={`doc-item ${selectedDoc === doc.id ? 'selected' : ''}`}
            onClick={() => setSelectedDoc(doc.id)}
          >
            {doc.type}
          </button>
        ))}
      </div>

      <div className="document-content">
        {selectedDocument ? (
          <>
            <div className="document-toolbar">
              <button onClick={() => handleExport(selectedDoc, 'docx')}>
                导出 Word
              </button>
              <button onClick={() => handleExport(selectedDoc, 'pdf')}>
                导出 PDF
              </button>
            </div>
            <div className="document-body">
              <pre>{selectedDocument.content}</pre>
            </div>
          </>
        ) : (
          <div className="document-placeholder">请选择一份文书</div>
        )}
      </div>
    </div>
  )
}
