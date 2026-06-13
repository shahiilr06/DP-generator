import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar.jsx'
import ChatTab from './components/ChatTab.jsx'
import AutoGenTab from './components/AutoGenTab.jsx'
import { getStatus, buildIndex } from './api.js'

export default function App() {
  const [activeTab, setActiveTab] = useState('chat')
  const [config, setConfig] = useState({
    apiKey: '',
    model: 'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free',
    epsilon: 1.0,
    maxExamples: 3,
  })
  const [indexedCount, setIndexedCount] = useState(0)
  const [isIndexing, setIsIndexing] = useState(false)
  const [indexError, setIndexError] = useState(null)

  // Hydrate status on mount
  useEffect(() => {
    getStatus()
      .then((data) => {
        if (data.indexed_count != null) setIndexedCount(data.indexed_count)
      })
      .catch(() => {})
  }, [])

  async function handleBuildIndex(maxDialogues) {
    setIsIndexing(true)
    setIndexError(null)
    try {
      const data = await buildIndex(maxDialogues)
      setIndexedCount(data.indexed_count ?? 0)
    } catch (err) {
      setIndexError(err.message)
    } finally {
      setIsIndexing(false)
    }
  }

  // Shared props for both tabs so they can gate on index status
  const sharedProps = {
    config,
    indexedCount,
    isIndexing,
    onBuildIndex: handleBuildIndex,
  }

  return (
    <div className="app">
      <Sidebar
        config={config}
        setConfig={setConfig}
        indexedCount={indexedCount}
        onBuildIndex={handleBuildIndex}
        isIndexing={isIndexing}
        indexError={indexError}
      />
      <div className="main-content">
        <header className="header">
          <div className="header-left">
            <nav className="tab-bar" role="tablist">
              <button
                className={`tab-btn${activeTab === 'chat' ? ' active' : ''}`}
                onClick={() => setActiveTab('chat')}
                role="tab"
                id="tab-chat"
                aria-selected={activeTab === 'chat'}
              >
                💬 Live Chat
              </button>
              <button
                className={`tab-btn${activeTab === 'autogen' ? ' active' : ''}`}
                onClick={() => setActiveTab('autogen')}
                role="tab"
                id="tab-autogen"
                aria-selected={activeTab === 'autogen'}
              >
                🤖 Auto-Generate
              </button>
            </nav>
          </div>

          <div className="header-right">
            {isIndexing && (
              <span
                className="indexed-badge"
                style={{
                  color: 'var(--amber)',
                  borderColor: 'rgba(251,191,36,0.3)',
                  background: 'rgba(251,191,36,0.08)',
                }}
              >
                <span
                  className="spinner spinner-sm"
                  style={{ borderTopColor: 'var(--amber)', borderColor: 'rgba(251,191,36,0.3)' }}
                />
                Building index…
              </span>
            )}
            {!isIndexing && indexedCount > 0 && (
              <span className="indexed-badge">
                <span className="indexed-badge-dot" />
                {indexedCount.toLocaleString()} dialogues indexed
              </span>
            )}
            {!isIndexing && indexedCount === 0 && (
              <span
                className="indexed-badge"
                style={{
                  color: 'var(--rose)',
                  borderColor: 'rgba(251,113,133,0.3)',
                  background: 'rgba(251,113,133,0.08)',
                }}
              >
                ⚠ Index not built
              </span>
            )}
          </div>
        </header>

        <div className="tab-content" role="tabpanel">
          {activeTab === 'chat' ? (
            <ChatTab {...sharedProps} />
          ) : (
            <AutoGenTab {...sharedProps} />
          )}
        </div>
      </div>
    </div>
  )
}
