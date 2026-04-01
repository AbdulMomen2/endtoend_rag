import { useState, useRef, useCallback } from 'react'
import { uploadDocument, pollJobStatus } from '../api/client.js'

export default function UploadModal({ onClose, onSuccess }) {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const inputRef = useRef(null)

  const accept = ['.pdf', '.docx']

  const pickFile = (f) => {
    if (!f) return
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    if (!accept.includes(ext)) {
      setError('Only PDF and DOCX files are supported.')
      return
    }
    if (f.size > 50 * 1024 * 1024) {
      setError('File must be under 50 MB.')
      return
    }
    setError('')
    setResult(null)
    setFile(f)
  }

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    pickFile(e.dataTransfer.files[0])
  }, [])

  const handleUpload = async () => {
    if (!file || uploading) return
    setUploading(true)
    setProgress(0)
    setError('')
    try {
      // Step 1: upload file and queue job
      const queued = await uploadDocument(file, setProgress)
      setProgress(100)

      // Step 2: poll until done
      const done = await pollJobStatus(
        queued.job_id,
        (job) => {
          if (job.status === 'processing') setProgress(100)
        }
      )
      setResult({ ...done.result, filename: queued.filename, size_kb: queued.size_kb })
      onSuccess?.(done.result)
    } catch (e) {
      setError(e.message || 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="modal__header">
          <div className="modal__title-row">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <h2>Upload Document</h2>
          </div>
          <button className="modal__close" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* Drop zone */}
        {!result && (
          <div
            className={`dropzone ${dragging ? 'dropzone--active' : ''} ${file ? 'dropzone--has-file' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => !file && inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx"
              style={{ display: 'none' }}
              onChange={e => pickFile(e.target.files[0])}
            />
            {file ? (
              <div className="dropzone__file">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
                <div>
                  <p className="dropzone__filename">{file.name}</p>
                  <p className="dropzone__filesize">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
                <button className="dropzone__remove" onClick={e => { e.stopPropagation(); setFile(null) }}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
            ) : (
              <>
                <svg className="dropzone__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <p className="dropzone__label">Drop your file here or <span>browse</span></p>
                <p className="dropzone__hint">PDF or DOCX · Max 50 MB</p>
              </>
            )}
          </div>
        )}

        {/* Progress */}
        {uploading && (
          <div className="upload-progress">
            <div className="upload-progress__bar">
              <div className="upload-progress__fill" style={{ width: `${progress}%` }} />
            </div>
            <p>{progress < 100 ? `Uploading… ${progress}%` : 'Processing document in background…'}</p>
          </div>
        )}

        {/* Error */}
        {error && <p className="modal__error">{error}</p>}

        {/* Success */}
        {result && (
          <div className="modal__success">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <div>
              <p className="modal__success-title">Document ingested successfully</p>
              <p className="modal__success-sub">
                {result.filename} · {result.size_kb} KB · {result.ingestion_ms}ms
              </p>
              <p className="modal__success-hint">You can now ask questions about this document.</p>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="modal__actions">
          {result ? (
            <button className="btn btn--primary" onClick={onClose}>Start chatting</button>
          ) : (
            <>
              <button className="btn btn--ghost" onClick={onClose}>Cancel</button>
              <button
                className="btn btn--primary"
                onClick={handleUpload}
                disabled={!file || uploading}
              >
                {uploading ? <><span className="spinner spinner--sm" /> Processing…</> : 'Upload & Ingest'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
