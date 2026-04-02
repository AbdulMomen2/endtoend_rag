import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

export default function Message({ message }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="msg msg--user">
        <div className="msg__bubble msg__bubble--user">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="msg msg--assistant">
      <div className="msg__avatar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 8v4l3 3"/>
        </svg>
      </div>
      <div className="msg__body">
        <div className="msg__content">
          <ReactMarkdown>{message.content || ''}</ReactMarkdown>
          {message.streaming && <span className="cursor" />}
        </div>

        {/* Hallucination guard badge */}
        {!message.streaming && message.content && (
          <div className="msg__badges">
            {message.conversational ? (
              <span className="badge badge--conversational">💬 Conversational</span>
            ) : message.fallback ? (
              <span className="badge badge--fallback">⚠ Not found in document</span>
            ) : message.sources?.length > 0 ? (
              <span className="badge badge--grounded">✓ Grounded in document</span>
            ) : null}
            {message.latency_ms && (
              <span className="badge badge--latency">{message.latency_ms}ms</span>
            )}
          </div>
        )}

        {/* Sources */}
        {message.sources?.length > 0 && !message.streaming && (
          <Sources sources={message.sources} />
        )}
      </div>
    </div>
  )
}

function Sources({ sources }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="sources">
      <button className="sources__toggle" onClick={() => setOpen(o => !o)}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        {sources.length} source{sources.length > 1 ? 's' : ''}
        <svg className={`sources__chevron ${open ? 'sources__chevron--open' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>

      {open && (
        <div className="sources__list">
          {sources.map((src, i) => (
            <div key={i} className="source">
              <div className="source__header">
                <span className="source__page">Page {src.page}</span>
                <span className="source__score">
                  relevance: {typeof src.similarity_score === 'number'
                    ? src.similarity_score.toFixed(4)
                    : src.similarity_score ?? 'N/A'}
                </span>
              </div>
              <p className="source__text">{src.text_snippet}</p>

            </div>
          ))}
        </div>
      )}
    </div>
  )
}
