const BASE = '/api/v1'

export async function streamChat({ query, sessionId, topK = 5, docId = null, provider = 'openai', model = 'gpt-4o-mini', onSources, onToken, onReplace, onDone, onError }) {
  try {
    const res = await fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        session_id: sessionId,
        top_k: topK,
        doc_id: docId,
        provider,
        model,
        use_cache: false
      })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }))
      // Pydantic returns detail as an array of error objects — flatten to string
      const detail = Array.isArray(err.detail)
        ? err.detail.map(e => e.msg || JSON.stringify(e)).join(', ')
        : (err.detail || 'Request failed')
      onError?.(detail)
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const e = JSON.parse(line.slice(6))
          if (e.type === 'sources') onSources?.(e.sources, e.conversational)
          else if (e.type === 'token') onToken?.(e.content)
          else if (e.type === 'replace') onReplace?.(e.content)
          else if (e.type === 'done') onDone?.(e.latency_ms, e.fallback)
          else if (e.type === 'error') onError?.(typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail))
        } catch {}
      }
    }
  } catch (err) {
    onError?.(err?.message || String(err) || 'Network error')
  }
}

export async function uploadDocument(file, onProgress) {
  const form = new FormData()
  form.append('file', file)
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BASE}/ingest`)
    xhr.upload.onprogress = e => {
      if (e.lengthComputable) onProgress?.(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText))
      } else {
        try { reject(new Error(JSON.parse(xhr.responseText).detail)) }
        catch { reject(new Error('Upload failed')) }
      }
    }
    xhr.onerror = () => reject(new Error('Network error'))
    xhr.send(form)
  })
}

export async function pollJobStatus(jobId, onStatus, intervalMs = 1500, timeoutMs = 120000) {
  const start = Date.now()
  return new Promise((resolve, reject) => {
    const check = async () => {
      if (Date.now() - start > timeoutMs) {
        reject(new Error('Ingestion timed out'))
        return
      }
      try {
        const res = await fetch(`${BASE}/ingest/jobs/${jobId}`)
        const job = await res.json()
        onStatus?.(job)
        if (job.status === 'done') { resolve(job); return }
        if (job.status === 'failed') { reject(new Error(job.error || 'Ingestion failed')); return }
        setTimeout(check, intervalMs)
      } catch (e) {
        reject(e)
      }
    }
    check()
  })
}

export async function getIngestStatus() {
  const res = await fetch(`${BASE}/ingest/status`)
  return res.json()
}

export async function clearSession(sessionId) {
  const res = await fetch(`${BASE}/session/${sessionId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to clear session')
  return res.json()
}

export async function getHealth() {
  const res = await fetch('/health')
  return res.json()
}

/** Transcribe audio blob via OpenAI Whisper (browser MediaRecorder output) */
export async function transcribeAudio(audioBlob) {
  const form = new FormData()
  form.append('file', audioBlob, 'voice.webm')
  const res = await fetch(`${BASE}/transcribe`, {
    method: 'POST',
    body: form
  })
  if (!res.ok) throw new Error('Transcription failed')
  const data = await res.json()
  return data.text
}
