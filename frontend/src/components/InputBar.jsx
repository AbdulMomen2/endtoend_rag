import { useState, useRef, useEffect, useCallback } from 'react'
import { transcribeAudio } from '../api/client.js'

export default function InputBar({ onSend, disabled, onUploadClick }) {
  const [value, setValue] = useState('')
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const textRef = useRef(null)
  const mediaRef = useRef(null)
  const chunksRef = useRef([])

  // Auto-resize
  useEffect(() => {
    if (textRef.current) {
      textRef.current.style.height = 'auto'
      textRef.current.style.height = Math.min(textRef.current.scrollHeight, 180) + 'px'
    }
  }, [value])

  const submit = useCallback(() => {
    const t = value.trim()
    if (!t || disabled) return
    onSend(t)
    setValue('')
    if (textRef.current) textRef.current.style.height = 'auto'
  }, [value, disabled, onSend])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      chunksRef.current = []
      mr.ondataavailable = e => chunksRef.current.push(e.data)
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        setTranscribing(true)
        try {
          const text = await transcribeAudio(blob)
          setValue(prev => prev ? prev + ' ' + text : text)
        } catch {
          setValue(prev => prev) // keep existing
        } finally {
          setTranscribing(false)
        }
      }
      mr.start()
      mediaRef.current = mr
      setRecording(true)
    } catch {
      alert('Microphone access denied or not available.')
    }
  }

  const stopRecording = () => {
    mediaRef.current?.stop()
    setRecording(false)
  }

  return (
    <div className="input-wrap">
      <div className={`input-box ${recording ? 'input-box--recording' : ''}`}>
        {/* Upload button */}
        <button
          type="button"
          className="input-icon-btn"
          onClick={onUploadClick}
          title="Upload document"
          disabled={disabled}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </button>

        <textarea
          ref={textRef}
          className="input-box__textarea"
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
          placeholder={recording ? '🎙 Recording… click stop when done' : transcribing ? 'Transcribing…' : 'Message RAG Assistant…'}
          rows={1}
          disabled={disabled || transcribing}
        />

        {/* Voice button */}
        <button
          type="button"
          className={`input-icon-btn ${recording ? 'input-icon-btn--active' : ''}`}
          onClick={recording ? stopRecording : startRecording}
          title={recording ? 'Stop recording' : 'Voice input'}
          disabled={disabled || transcribing}
        >
          {transcribing ? (
            <span className="spinner spinner--sm" />
          ) : recording ? (
            <svg viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2"/>
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          )}
        </button>

        {/* Send button */}
        <button
          className="input-box__send"
          onClick={submit}
          disabled={disabled || !value.trim() || recording}
          aria-label="Send"
        >
          {disabled
            ? <span className="spinner spinner--sm" />
            : <svg viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
          }
        </button>
      </div>
    </div>
  )
}
