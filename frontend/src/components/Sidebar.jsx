import { useState } from 'react'

export default function Sidebar({
  config,
  setConfig,
  indexedCount,
  onBuildIndex,
  isIndexing,
  indexError,
}) {
  const [maxDialogues, setMaxDialogues] = useState(500)
  const [buildSuccess, setBuildSuccess] = useState(false)

  function updateConfig(key, value) {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }

  async function handleBuild() {
    setBuildSuccess(false)
    await onBuildIndex(maxDialogues)
    setBuildSuccess(true)
    setTimeout(() => setBuildSuccess(false), 5000)
  }

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon-wrap">🛡️</div>
          <div>
            <div className="sidebar-title">DP RAG Chatbot</div>
          </div>
        </div>
        <div className="sidebar-subtitle">Differential Privacy · RAG · LLM</div>
      </div>

      {/* Dataset section */}
      <div className="sidebar-section">
        <div className="sidebar-section-label">📦 Dataset Index</div>
        <div className="control-group">
          <label>Max Dialogues</label>
          <input
            className="input-field"
            type="number"
            min={10}
            max={10000}
            step={50}
            value={maxDialogues}
            onChange={(e) => setMaxDialogues(Number(e.target.value))}
          />
        </div>
        <button
          className="btn btn-primary btn-full"
          onClick={handleBuild}
          disabled={isIndexing}
          id="build-index-btn"
        >
          {isIndexing ? (
            <>
              <span className="spinner spinner-sm" />
              Building Index…
            </>
          ) : (
            '⚡ Build Index'
          )}
        </button>
        {buildSuccess && !indexError && (
          <div className="inline-success">✓ Index built — {indexedCount.toLocaleString()} dialogues</div>
        )}
        {indexError && (
          <div className="inline-error">⚠ {indexError}</div>
        )}
      </div>

      <div className="sidebar-divider" />

      {/* LLM section */}
      <div className="sidebar-section">
        <div className="sidebar-section-label">🤖 LLM Config</div>
        <div className="control-group">
          <label>OpenRouter API Key</label>
          <input
            className="input-field"
            type="password"
            placeholder="sk-or-v1-••••••••••"
            value={config.apiKey}
            onChange={(e) => updateConfig('apiKey', e.target.value)}
            autoComplete="off"
            id="api-key-input"
          />
        </div>
        <div className="control-group">
          <label>Model</label>
          <input
            className="input-field"
            type="text"
            placeholder="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
            value={config.model}
            onChange={(e) => updateConfig('model', e.target.value)}
            id="model-input"
          />
        </div>
      </div>

      <div className="sidebar-divider" />

      {/* Privacy section */}
      <div className="sidebar-section">
        <div className="sidebar-section-label">🔒 Privacy Budget</div>

        <div className="slider-container">
          <div className="slider-header">
            <span className="slider-label">Epsilon (DP noise)</span>
            <span className="slider-value">{config.epsilon.toFixed(1)}</span>
          </div>
          <input
            type="range"
            min={0.1}
            max={10}
            step={0.1}
            value={config.epsilon}
            onChange={(e) => updateConfig('epsilon', parseFloat(e.target.value))}
            id="epsilon-slider"
          />
          <div className="slider-hints">
            <span className="slider-hint">0.1 (strict)</span>
            <span className="slider-hint">10 (loose)</span>
          </div>
        </div>

        <div className="slider-container">
          <div className="slider-header">
            <span className="slider-label">Max RAG Examples</span>
            <span className="slider-value">{config.maxExamples}</span>
          </div>
          <input
            type="range"
            min={1}
            max={8}
            step={1}
            value={config.maxExamples}
            onChange={(e) => updateConfig('maxExamples', parseInt(e.target.value))}
            id="max-examples-slider"
          />
          <div className="slider-hints">
            <span className="slider-hint">1</span>
            <span className="slider-hint">8</span>
          </div>
        </div>
      </div>

      <div className="sidebar-divider" />

      {/* Stats */}
      <div>
        <div className="sidebar-section-label" style={{ padding: '12px 16px 8px' }}>
          📊 Stats
        </div>
        <div className="stat-grid">
          <div className="stat-box">
            <div className="stat-value">{indexedCount.toLocaleString()}</div>
            <div className="stat-label">Indexed</div>
          </div>
          <div className="stat-box">
            <div className="stat-value">{config.epsilon.toFixed(1)}</div>
            <div className="stat-label">Epsilon</div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <span>⚙</span>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {config.model || 'No model set'}
        </span>
      </div>
    </aside>
  )
}
