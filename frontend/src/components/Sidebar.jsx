import { useState } from 'react'

export default function Sidebar({ threads, activeId, onSelect, onCreate, onDelete, isOpen, onToggle, onUpload }) {
  const [hoverId, setHoverId] = useState(null)

  return (
    <aside className={`sidebar ${isOpen ? 'sidebar--open' : 'sidebar--closed'}`}>
      <div className="sidebar__header">
        <button className="sidebar__toggle" onClick={onToggle} aria-label="Toggle sidebar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
        {isOpen && <span className="sidebar__brand">RAG Assistant</span>}
      </div>

      {isOpen && (
        <>
          <div className="sidebar__actions">
            <button className="sidebar__new-btn" onClick={onCreate}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 5v14M5 12h14"/>
              </svg>
              New chat
            </button>
            <button className="sidebar__upload-btn" onClick={onUpload}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              Upload doc
            </button>
          </div>

          <div className="sidebar__threads">
            {threads.length === 0 && (
              <p className="sidebar__empty">No conversations yet</p>
            )}
            {threads.map(thread => (
              <div
                key={thread.id}
                className={`thread-item ${thread.id === activeId ? 'thread-item--active' : ''}`}
                onClick={() => onSelect(thread.id)}
                onMouseEnter={() => setHoverId(thread.id)}
                onMouseLeave={() => setHoverId(null)}
              >
                <svg className="thread-item__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <div className="thread-item__info">
                  <span className="thread-item__title">{thread.title}</span>
                  {thread.docName && (
                    <span className="thread-item__doc">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                      </svg>
                      {thread.docName.length > 22 ? thread.docName.slice(0, 22) + '…' : thread.docName}
                    </span>
                  )}
                </div>
                {(hoverId === thread.id || thread.id === activeId) && (
                  <button
                    className="thread-item__delete"
                    onClick={e => { e.stopPropagation(); onDelete(thread.id) }}
                    aria-label="Delete"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <polyline points="3 6 5 6 21 6"/>
                      <path d="M19 6l-1 14H6L5 6"/>
                      <path d="M10 11v6M14 11v6"/>
                      <path d="M9 6V4h6v2"/>
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="sidebar__footer">
            <div className="sidebar__model-badge">
              <span className="badge-dot" />
              GPT-4o-mini · Hybrid RAG
            </div>
          </div>
        </>
      )}
    </aside>
  )
}
