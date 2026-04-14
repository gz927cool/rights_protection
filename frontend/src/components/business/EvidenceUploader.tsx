import React, { useState } from 'react'
import { evidence as evidenceApi } from '../../services/api'

interface EvidenceUploaderProps {
  caseId: string
  onUploadComplete?: () => void
}

export function EvidenceUploader({ caseId, onUploadComplete }: EvidenceUploaderProps) {
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  const handleUpload = async (files: FileList) => {
    setUploading(true)
    try {
      for (const file of Array.from(files)) {
        await evidenceApi.upload(caseId, file)
      }
      onUploadComplete?.()
    } catch (error) {
      console.error('Upload failed:', error)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div
      className={`evidence-uploader ${dragOver ? 'drag-over' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragOver(false)
        if (e.dataTransfer.files.length > 0) {
          handleUpload(e.dataTransfer.files)
        }
      }}
    >
      <input
        type="file"
        multiple
        accept="image/*,.pdf"
        onChange={(e) => e.target.files && handleUpload(e.target.files)}
        className="file-input"
      />
      <div className="upload-content">
        <span className="upload-icon">📎</span>
        <span className="upload-text">
          {uploading ? '上传中...' : '点击或拖拽上传证据'}
        </span>
      </div>
    </div>
  )
}
