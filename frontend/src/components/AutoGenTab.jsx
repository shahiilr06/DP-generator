import { useState, useRef, useEffect } from 'react'
import { streamAutogen } from '../api.js'

/** Download utility */
function downloadFile(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function dialogueToCSV(dialogue) {
  const header = 'turn,role,text\n'
  const rows = dialogue
    .map((item, i) =>
      `${i + 1},${item.role},"${String(item.text ?? '').replace(/"/g, '""')}"`
    )
    .join('\n')
  return header + rows
}

export default function AutoGenTab({ config, indexedCount, isIndexing, onBuildIndex }) {
  const [dialogue, setDialogue] = useState([])
  const [isGenerating, setIsGenerating] = useState(false)
  const [currentTurn, setCurrentTurn] = useState(0)
  const [totalTurns, setTotalTurns] = useState(0)
  const [currentStatus, setCurrentStatus] = useState('idle')
  const [nTurns, setNTurns] = useState(6)
  const [temperature, setTemperature] = useState(0.8)
  const [streamingAgentText, setStreamingAgentText] = useState('')
  const [completedDialogue, setCompletedDialogue] = useState(null)
  const [error, setError] = useState(null)
  const [localBuilding, setLocalBuilding] = useState(false)

  const bottomRef = useRef(null)
  const indexReady = indexedCount > 0

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [dialogue, streamingAgentText])

  function handleClear() {
    setDialogue([])
    setCompletedDialogue(null)
    setStreamingAgentText('')
    setCurrentTurn(0)
    setTotalTurns(0)
    setCurrentStatus('idle')
    setError(null)
  }

  async function handleQuickBuild() {
    setLocalBuilding(true)
    try {
      await onBuildIndex(500)
    } finally {
      setLocalBuilding(false)
    }
  }

  async function handleStart() {
    if (isGenerating || !indexReady) return
    handleClear()
    setIsGenerating(true)
    setTotalTurns(nTurns)
    setError(null)

    try {
      await streamAutogen(
        {
          nTurns,
          temperature,
          epsilon: config.epsilon,
          maxExamples: config.maxExamples,
          model: config.model,
          apiKey: config.apiKey,
        },
        // onCustomer
        (text, turn) => {
          setCurrentTurn(turn)
          setCurrentStatus('customer')
          setDialogue((prev) => [...prev, { role: 'customer', text, turn }])
        },
        // onAgentChunk
        (text, turn) => {
          setCurrentTurn(turn)
          setCurrentStatus('agent')
          setStreamingAgentText((prev) => prev + text)
        },
        // onAgentDone
        (text, turn) => {
          setCurrentStatus('idle')
          setStreamingAgentText('')
          setDialogue((prev) => [...prev, { role: 'agent', text, turn }])
        },
        // onComplete
        (fullDialogue) => {
          setCompletedDialogue(fullDialogue)
          setCurrentStatus('idle')
          setStreamingAgentText('')
        }
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setIsGenerating(false)
      setCurrentStatus('idle')
    }
  }

  function handleDownloadJSON() {
    const data = completedDialogue || dialogue
    downloadFile(JSON.stringify(data, null, 2), `dialogue-${Date.now()}.json`, 'application/json')
  }

  function handleDownloadCSV() {
    const data = completedDialogue || dialogue
    downloadFile(dialogueToCSV(data), `dialogue-${Date.now()}.csv`, 'text/csv')
  }

  function renderDialogue() {
    const items = []
    let lastTurn = null

    dialogue.forEach((msg, idx) => {
      if (lastTurn !== null && msg.turn !== lastTurn && msg.role === 'customer') {
        items.push(
          <div key={`div-${idx}`} className="turn-divider">
            <div className="turn-divider-line" />
            <div className="turn-divider-label">Turn {msg.turn + 1}</div>
            <div className="turn-divider-line" />
          </div>
        )
      }
      lastTurn = msg.turn

      if (msg.role === 'customer') {
        items.push(
          <div key={`msg-${idx}`} className="cust-bubble">
            <div className="bubble-role-cust">👤 Customer · Round {msg.turn + 1}</div>
            {msg.text}
          </div>
        )
      } else {
        items.push(
          <div key={`msg-${idx}`} className="agent-bubble">
            <div className="bubble-role-agent">🤖 Support Agent · Round {msg.turn + 1}</div>
            {msg.text}
          </div>
        )
      }
    })

    return items
  }

  const progressPct = totalTurns > 0
    ? Math.min(100, ((currentTurn + 1) / totalTurns) * 100)
    : 0
  const hasContent = dialogue.length > 0 || !!streamingAgentText
  const isDone = !!completedDialogue

  // ── Index not ready: show a blocking notice ───────────────────
  if (!indexReady) {
    return (
      <div className="autogen-container">
        <div className="index-gate">
          <div className="index-gate-icon">🗂️</div>
          <div className="index-gate-title">Index Required</div>
          <div className="index-gate-body">
            Auto-Generate needs the dialogue index to retrieve privacy-safe examples.
            <br />
            Click <strong>Build Index</strong> below (or use the sidebar) to get started.
          </div>
          <div className="index-gate-steps">
            <div className="index-gate-step">
              <span className="index-gate-step-num">1</span>
              <span>Set <em>Max Dialogues</em> in the sidebar (500 is a good start)</span>
            </div>
            <div className="index-gate-step">
              <span className="index-gate-step-num">2</span>
              <span>Click <strong>Build Index</strong> and wait for it to finish</span>
            </div>
            <div className="index-gate-step">
              <span className="index-gate-step-num">3</span>
              <span>Return here and click <strong>▶ Start Generation</strong></span>
            </div>
          </div>
          <button
            className="btn btn-primary index-gate-btn"
            onClick={handleQuickBuild}
            disabled={localBuilding || isIndexing}
            id="quick-build-btn"
          >
            {localBuilding || isIndexing ? (
              <>
                <span className="spinner spinner-sm" />
                Building index… this may take a minute
              </>
            ) : (
              '⚡ Build Index Now (500 dialogues)'
            )}
          </button>
          {(localBuilding || isIndexing) && (
            <div className="index-gate-progress">
              <div className="progress-bar" style={{ width: '100%' }}>
                <div className="progress-bar-fill" style={{ width: '100%', animation: 'shimmer-progress 1.5s linear infinite' }} />
              </div>
              <span className="index-gate-progress-label">Embedding and indexing dialogues…</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Index ready: normal UI ─────────────────────────────────────
  return (
    <div className="autogen-container">
      {/* Controls */}
      <div className="autogen-controls">
        <div className="autogen-control-item">
          <label>Turn Pairs</label>
          <div className="autogen-control-row">
            <input
              type="range"
              min={2}
              max={20}
              step={1}
              value={nTurns}
              onChange={(e) => setNTurns(Number(e.target.value))}
              disabled={isGenerating}
              style={{ width: 140 }}
              id="n-turns-slider"
            />
            <span className="autogen-control-value">{nTurns}</span>
          </div>
        </div>

        <div className="autogen-control-item">
          <label>Temperature</label>
          <div className="autogen-control-row">
            <input
              type="range"
              min={0.5}
              max={1.2}
              step={0.05}
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              disabled={isGenerating}
              style={{ width: 100 }}
              id="temperature-slider"
            />
            <span className="autogen-control-value">{temperature.toFixed(2)}</span>
          </div>
        </div>

        <div className="autogen-btn-row">
          <button
            className="btn btn-secondary"
            onClick={handleClear}
            disabled={isGenerating || !hasContent}
            id="autogen-clear-btn"
          >
            🗑 Clear
          </button>
          <button
            className="btn btn-primary"
            onClick={handleStart}
            disabled={isGenerating}
            id="autogen-start-btn"
          >
            {isGenerating ? (
              <>
                <span className="spinner spinner-sm" />
                Generating…
              </>
            ) : (
              '▶ Start Generation'
            )}
          </button>
        </div>
      </div>

      {/* Progress bar */}
      {isGenerating && (
        <div className="progress-wrapper">
          <div className="progress-header">
            <span className="progress-label">Turn {currentTurn + 1} of {totalTurns}</span>
            <span
              className={`status-badge ${
                currentStatus === 'customer' ? 'customer'
                : currentStatus === 'agent' ? 'agent'
                : 'idle'
              }`}
            >
              {currentStatus === 'customer'
                ? '👤 Customer question'
                : currentStatus === 'agent'
                ? '🤖 Agent responding'
                : '⏳ Processing'}
            </span>
          </div>
          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
          </div>
        </div>
      )}

      {/* Dialogue feed */}
      <div className="autogen-dialogue">
        {!hasContent && !isGenerating && (
          <div className="autogen-empty">
            <div className="autogen-empty-glow">🤖</div>
            <div className="autogen-empty-title">Auto-Generate Synthetic Dialogues</div>
            <div className="autogen-empty-sub">
              Configure turn pairs and temperature above, then click{' '}
              <strong style={{ color: 'var(--primary-3)' }}>▶ Start Generation</strong>.{' '}
              Each run produces a unique privacy-safe customer ↔ agent conversation.
            </div>
          </div>
        )}

        {hasContent && (
          <div className="turn-divider" style={{ opacity: 0.3 }}>
            <div className="turn-divider-line" />
            <div className="turn-divider-label">Turn 1</div>
            <div className="turn-divider-line" />
          </div>
        )}

        {renderDialogue()}

        {streamingAgentText && (
          <div className="agent-bubble">
            <div className="bubble-role-agent">🤖 Support Agent · Round {currentTurn + 1}</div>
            {streamingAgentText}
            <span className="streaming-cursor">▌</span>
          </div>
        )}

        {error && (
          <div className="inline-error">⚠ {error}</div>
        )}

        {isDone && !isGenerating && (
          <div className="completion-pill">
            ✓ Generation complete — {dialogue.length} messages across {nTurns} turns
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Download bar */}
      {isDone && !isGenerating && (
        <div className="download-bar">
          <span className="download-bar-label">⬇ Export dataset:</span>
          <button className="btn btn-secondary" onClick={handleDownloadJSON} id="download-json-btn">
            📄 JSON
          </button>
          <button className="btn btn-secondary" onClick={handleDownloadCSV} id="download-csv-btn">
            📊 CSV
          </button>
        </div>
      )}
    </div>
  )
}
