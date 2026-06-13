import { useState, useEffect, useRef, useCallback } from 'react'
import { streamChat, clearChat, getRandomQuestion } from '../api.js'

/**
 * Render assistant text, wrapping PII tokens in styled spans.
 */
function renderWithPII(text, piiList) {
  if (!piiList || piiList.length === 0) return text

  const tokens = piiList.map((p) =>
    typeof p === 'string' ? p : p.replacement ?? p.original ?? ''
  ).filter(Boolean)

  if (tokens.length === 0) return text

  const escaped = tokens.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const pattern = new RegExp(`(${escaped.join('|')})`, 'g')
  const parts = text.split(pattern)

  return parts.map((part, i) =>
    tokens.includes(part)
      ? <span key={i} className="pii-badge">{part}</span>
      : part
  )
}

export default function ChatTab({ config, indexedCount, isIndexing, onBuildIndex }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [retrievedContext, setRetrievedContext] = useState([])
  const [showContext, setShowContext] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [error, setError] = useState(null)
  const [isLoadingRandom, setIsLoadingRandom] = useState(false)
  const [dismissedWarning, setDismissedWarning] = useState(false)

  const indexReady = indexedCount > 0

  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const abortRef = useRef(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  async function handleRandomQuestion() {
    setIsLoadingRandom(true)
    try {
      const data = await getRandomQuestion()
      setInput(data.question ?? data.text ?? '')
      inputRef.current?.focus()
    } catch {
      // silently ignore
    } finally {
      setIsLoadingRandom(false)
    }
  }

  async function handleClear() {
    try { await clearChat() } catch {}
    setMessages([])
    setRetrievedContext([])
    setStreamingText('')
    setError(null)
  }

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || isStreaming) return

    setInput('')
    setError(null)
    setIsStreaming(true)
    abortRef.current = false

    setMessages((prev) => [
      ...prev,
      { role: 'user', text, sanitized: text, pii: [] },
    ])
    setStreamingText('')

    let accText = ''
    let doneCalled = false

    try {
      await streamChat(
        text,
        config,
        (chunk) => {
          if (abortRef.current) return
          accText += chunk
          setStreamingText(accText)
        },
        (pii, sanitizedMessage) => {
          doneCalled = true
          if (abortRef.current) return
          setMessages((prev) => {
            const updated = [...prev]
            const lastUser = [...updated].reverse().find((m) => m.role === 'user')
            if (lastUser) {
              lastUser.sanitized = sanitizedMessage || lastUser.text
              lastUser.pii = pii || []
            }
            return [
              ...updated,
              { role: 'assistant', text: accText, pii: pii || [] },
            ]
          })
          setStreamingText('')
        },
        (count, examples) => {
          setRetrievedContext(examples || [])
        }
      )
    } catch (err) {
      setError(err.message)
      if (accText) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', text: accText, pii: [] },
        ])
        setStreamingText('')
      }
    } finally {
      if (!doneCalled && accText && !abortRef.current) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', text: accText, pii: [] },
        ])
        setStreamingText('')
      }
      setIsStreaming(false)
    }
  }, [input, isStreaming, config])

  const hasMessages = messages.length > 0
  const hasContext = retrievedContext.length > 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
      {/* Index warning banner — non-blocking, RAG just won't work */}
      {!indexReady && !dismissedWarning && (
        <div className="index-warning-banner">
          <span className="index-warning-icon">⚡</span>
          <span className="index-warning-text">
            <strong>No index built yet.</strong> RAG context won't be retrieved.
            {' '}
            <button
              className="index-warning-link"
              onClick={() => onBuildIndex(500)}
              disabled={isIndexing}
            >
              {isIndexing ? 'Building…' : 'Build index now'}
            </button>
          </span>
          <button
            className="index-warning-close"
            onClick={() => setDismissedWarning(true)}
            title="Dismiss"
          >
            ✕
          </button>
        </div>
      )}
      {/* Messages */}
      <div className="chat-messages">
        {!hasMessages && !isStreaming && (
          <div className="chat-empty">
            <div className="chat-empty-glow">💬</div>
            <div className="chat-empty-text">Start a Conversation</div>
            <div className="chat-empty-hint">
              Ask anything about customer service — RAG retrieves relevant examples with differential privacy protection.
            </div>
            <div className="chat-empty-tips">
              <span className="chat-tip-pill">🎲 Use the dice to get a random question</span>
              <span className="chat-tip-pill">🔒 PII is automatically detected &amp; anonymized</span>
              <span className="chat-tip-pill">📎 See retrieved context below each response</span>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message-row ${msg.role}`}>
            <div className="bubble-role">
              {msg.role === 'user' ? '👤 You' : '🤖 Assistant'}
            </div>
            {msg.role === 'user' ? (
              <div className="user-bubble">
                {msg.pii && msg.pii.length > 0
                  ? renderWithPII(msg.sanitized || msg.text, msg.pii)
                  : (msg.sanitized || msg.text)}
              </div>
            ) : (
              <div className="assistant-bubble">
                {renderWithPII(msg.text, msg.pii)}
              </div>
            )}
          </div>
        ))}

        {/* Streaming bubble */}
        {isStreaming && (
          <div className="message-row assistant">
            <div className="bubble-role">🤖 Assistant</div>
            <div className="assistant-bubble">
              {streamingText || <span style={{ color: 'var(--text-dim)' }}>Thinking…</span>}
              <span className="streaming-cursor">▌</span>
            </div>
          </div>
        )}

        {error && (
          <div className="inline-error" style={{ margin: '4px 0' }}>⚠ {error}</div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* RAG Context Toggle */}
      {hasContext && (
        <>
          <div
            className="context-panel-header"
            onClick={() => setShowContext((v) => !v)}
            id="context-toggle"
          >
            <span>📎 {retrievedContext.length} retrieved context example{retrievedContext.length !== 1 ? 's' : ''}</span>
            <span style={{ fontSize: 10 }}>{showContext ? '▲ Hide' : '▼ Show'}</span>
          </div>
          {showContext && (
            <div className="context-panel">
              <div className="context-panel-inner">
                <div className="context-list">
                  {retrievedContext.map((ex, i) => (
                    <div key={i} className="context-item">
                      <div className="context-item-label">Example {i + 1}</div>
                      {typeof ex === 'string'
                        ? ex
                        : ex.snippet ?? ex.text ?? ex.content ?? JSON.stringify(ex)}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Input bar */}
      <div className="chat-input-bar">
        <div className="chat-input-wrapper">
          <textarea
            ref={inputRef}
            className="chat-input"
            rows={1}
            placeholder="Ask a customer service question… (Enter to send)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
            id="chat-input"
          />
        </div>
        <div className="chat-input-actions">
          <button
            className="btn btn-secondary"
            onClick={handleRandomQuestion}
            disabled={isStreaming || isLoadingRandom}
            title="Random question"
            id="random-question-btn"
          >
            {isLoadingRandom ? <span className="spinner spinner-sm" /> : '🎲'}
          </button>
          <button
            className="btn btn-danger"
            onClick={handleClear}
            disabled={isStreaming || !hasMessages}
            title="Clear chat"
            id="clear-chat-btn"
          >
            🗑
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            id="send-btn"
          >
            {isStreaming ? (
              <>
                <span className="spinner spinner-sm" />
                Generating
              </>
            ) : (
              '↑ Send'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
