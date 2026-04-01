import { useEffect, useRef } from 'react'
import Message from './Message.jsx'
import InputBar from './InputBar.jsx'

const SUGGESTIONS = [
  'What is this document about?',
  'What dataset is used and what is its size?',
  'What are the key findings and results?',
  'Explain the methodology in detail.',
  'What model architecture is proposed?',
]

export default function ChatArea({ thread, isStreaming, onSend, onUploadClick }) {
  const bottomRef = useRef(null)
  const messages = thread?.messages || []
  const docName = thread?.docName || null

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="chat-area">
      {/* Document context banner */}
      {docName && (
        <div className="chat-area__doc-banner">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          Scoped to: <strong>{docName}</strong>
          <span className="chat-area__doc-hint">Answers restricted to this document only</span>
        </div>
      )}
      <div className="chat-area__messages">
        {messages.length === 0 ? (
          <div className="welcome">
            <div className="welcome__icon">
              <svg viewBox="0 0 48 48" fill="none">
                <circle cx="24" cy="24" r="23" stroke="var(--accent)" strokeWidth="1.5" opacity="0.3"/>
                <path d="M14 24h20M24 14v20" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <h1>What would you like to know?</h1>
            <p>Ask anything about the ingested document. I'll answer strictly from its contents.</p>
            <button className="welcome__upload-btn" onClick={onUploadClick}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              Upload a document to get started
            </button>
            <p className="welcome__or">or ask about the already ingested document</p>
            <div className="welcome__chips">
              {SUGGESTIONS.map(s => (
                <button key={s} className="chip" onClick={() => onSend(s)}>{s}</button>
              ))}
            </div>
          </div>
        ) : (
          messages.map(msg => <Message key={msg.id} message={msg} />)
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-area__input">
        <InputBar onSend={onSend} disabled={isStreaming} onUploadClick={onUploadClick} />
        <p className="chat-area__disclaimer">
          Answers are grounded strictly in the document · Citations shown as (Page N) · 🎙 Voice input supported
        </p>
      </div>
    </div>
  )
}
