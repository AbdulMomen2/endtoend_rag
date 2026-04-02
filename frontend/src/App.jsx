import { useState, useCallback, useEffect } from 'react'
import { v4 as uuidv4 } from 'uuid'
import Sidebar from './components/Sidebar.jsx'
import ChatArea from './components/ChatArea.jsx'
import UploadModal from './components/UploadModal.jsx'
import { streamChat, clearSession } from './api/client.js'

const THREADS_KEY = 'rag_threads'

function loadThreads() {
  try { return JSON.parse(localStorage.getItem(THREADS_KEY)) || [] } catch { return [] }
}
function saveThreads(t) { localStorage.setItem(THREADS_KEY, JSON.stringify(t)) }

export default function App() {
  const [threads, setThreads] = useState(loadThreads)
  const [activeId, setActiveId] = useState(() => {
    const t = loadThreads(); return t.length > 0 ? t[0].id : null
  })
  const [isStreaming, setIsStreaming] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [showUpload, setShowUpload] = useState(false)

  const activeThread = threads.find(t => t.id === activeId) || null

  useEffect(() => { saveThreads(threads) }, [threads])

  const createThread = useCallback((docId = null, docName = null) => {
    const id = uuidv4()
    const thread = {
      id,
      title: docName ? `Chat: ${docName}` : 'New conversation',
      messages: [],
      createdAt: Date.now(),
      docId,
      docName,
      provider: 'openai',
      model: 'gpt-4o-mini',
    }
    setThreads(prev => [thread, ...prev])
    setActiveId(id)
    return id
  }, [])

  useEffect(() => {
    if (threads.length === 0) createThread()
  }, [])

  const deleteThread = useCallback(async (id) => {
    try { await clearSession(id) } catch {}
    setThreads(prev => prev.filter(t => t.id !== id))
    setActiveId(prev => {
      if (prev !== id) return prev
      const remaining = threads.filter(t => t.id !== id)
      return remaining.length > 0 ? remaining[0].id : null
    })
  }, [threads])

  const updateThread = useCallback((id, updater) => {
    setThreads(prev => prev.map(t => t.id === id ? updater(t) : t))
  }, [])

  const handleSend = useCallback(async (query) => {
    if (isStreaming || !activeId) return
    const msgId = uuidv4()
    const thread = threads.find(t => t.id === activeId)

    updateThread(activeId, t => ({
      ...t,
      title: t.messages.length === 0 && !t.docName ? query.slice(0, 40) : t.title,
      messages: [...t.messages, { id: uuidv4(), role: 'user', content: query }]
    }))
    updateThread(activeId, t => ({
      ...t,
      messages: [...t.messages, { id: msgId, role: 'assistant', content: '', streaming: true, sources: [] }]
    }))

    setIsStreaming(true)

    await streamChat({
      query,
      sessionId: activeId,
      topK: 5,
      docId: thread?.docId || null,
      provider: thread?.provider || 'openai',
      model: thread?.model || 'gpt-4o-mini',
      onSources: (sources, conversational) => {
        updateThread(activeId, t => ({
          ...t,
          messages: t.messages.map(m => m.id === msgId ? { ...m, sources, conversational } : m)
        }))
      },
      onToken: (token) => {
        updateThread(activeId, t => ({
          ...t,
          messages: t.messages.map(m => m.id === msgId ? { ...m, content: m.content + token } : m)
        }))
      },
      onReplace: (content) => {
        updateThread(activeId, t => ({
          ...t,
          messages: t.messages.map(m => m.id === msgId ? { ...m, content, fallback: true } : m)
        }))
      },
      onDone: (latency_ms, fallback) => {
        updateThread(activeId, t => ({
          ...t,
          messages: t.messages.map(m => m.id === msgId ? { ...m, streaming: false, latency_ms, fallback } : m)
        }))
        setIsStreaming(false)
      },
      onError: (detail) => {
        const msg = typeof detail === 'string' ? detail : JSON.stringify(detail)
        updateThread(activeId, t => ({
          ...t,
          messages: t.messages.map(m => m.id === msgId ? { ...m, content: `⚠️ ${msg}`, streaming: false } : m)
        }))
        setIsStreaming(false)
      }
    })
  }, [isStreaming, activeId, updateThread, threads])

  // Called after successful upload — create a new thread bound to the document
  const handleUploadSuccess = useCallback((result) => {
    setShowUpload(false)
    createThread(result.doc_id, result.filename)
  }, [createThread])

  const handleModelChange = useCallback((provider, model) => {
    if (!activeId) return
    updateThread(activeId, t => ({ ...t, provider, model }))
  }, [activeId, updateThread])

  return (
    <div className="app" data-sidebar={sidebarOpen}>
      <Sidebar
        threads={threads}
        activeId={activeId}
        onSelect={setActiveId}
        onCreate={() => createThread()}
        onDelete={deleteThread}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(o => !o)}
        onUpload={() => setShowUpload(true)}
      />
      <ChatArea
        thread={activeThread}
        isStreaming={isStreaming}
        onSend={handleSend}
        onUploadClick={() => setShowUpload(true)}
        onModelChange={handleModelChange}
      />
      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onSuccess={handleUploadSuccess}
        />
      )}
    </div>
  )
}
