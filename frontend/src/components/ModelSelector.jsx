import { useState, useEffect } from 'react'

const MODELS = {
  openai: {
    label: 'OpenAI',
    icon: '🤖',
    models: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'],
  },
  gemini: {
    label: 'Gemini',
    icon: '✨',
    models: ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash'],
  },
  groq: {
    label: 'Groq',
    icon: '⚡',
    models: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768'],
  },
}

export default function ModelSelector({ provider, model, onChange, disabled }) {
  const [open, setOpen] = useState(false)

  const currentProvider = MODELS[provider] || MODELS.openai
  const currentModel = model || currentProvider.models[0]

  const select = (p, m) => {
    onChange(p, m)
    setOpen(false)
  }

  return (
    <div className="model-selector">
      <button
        className="model-selector__trigger"
        onClick={() => setOpen(o => !o)}
        disabled={disabled}
        title="Change AI model"
      >
        <span>{currentProvider.icon}</span>
        <span className="model-selector__name">{currentModel}</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>

      {open && (
        <div className="model-selector__dropdown">
          {Object.entries(MODELS).map(([pKey, pInfo]) => (
            <div key={pKey} className="model-selector__group">
              <div className="model-selector__group-label">
                {pInfo.icon} {pInfo.label}
              </div>
              {pInfo.models.map(m => (
                <button
                  key={m}
                  className={`model-selector__option ${pKey === provider && m === currentModel ? 'model-selector__option--active' : ''}`}
                  onClick={() => select(pKey, m)}
                >
                  {m}
                  {pKey === 'groq' && <span className="model-selector__free">free</span>}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
