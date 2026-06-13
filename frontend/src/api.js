/**
 * api.js — All API calls to the FastAPI backend.
 * The Vite dev server proxies /api → http://localhost:8000
 */

/** POST /api/build-index */
export async function buildIndex(maxDialogues) {
  const res = await fetch('/api/build-index', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ max_dialogues: maxDialogues }),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Build index failed: ${res.status} ${err}`)
  }
  return res.json()
}

/** GET /api/status */
export async function getStatus() {
  const res = await fetch('/api/status')
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Status failed: ${res.status} ${err}`)
  }
  return res.json()
}

/** POST /api/chat/clear */
export async function clearChat() {
  const res = await fetch('/api/chat/clear', { method: 'POST' })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Clear chat failed: ${res.status} ${err}`)
  }
  return res.json()
}

/** GET /api/random-question */
export async function getRandomQuestion() {
  const res = await fetch('/api/random-question')
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Random question failed: ${res.status} ${err}`)
  }
  return res.json()
}

/**
 * POST /api/chat — SSE streaming chat.
 *
 * @param {string} message
 * @param {{ apiKey: string, model: string, epsilon: number, maxExamples: number }} config
 * @param {(text: string) => void} onChunk
 * @param {(pii: any[], sanitizedMessage: string) => void} onDone
 * @param {(count: number, examples: any[]) => void} onRetrieved
 */
export async function streamChat(message, config, onChunk, onDone, onRetrieved) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      api_key: config.apiKey,
      model: config.model,
      epsilon: config.epsilon,
      max_examples: config.maxExamples,
    }),
  })

  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Chat failed: ${res.status} ${err}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // keep incomplete line in buffer

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) continue
      const jsonStr = trimmed.slice(5).trim()
      if (!jsonStr || jsonStr === '[DONE]') continue

      let event
      try {
        event = JSON.parse(jsonStr)
      } catch {
        continue
      }

      if (event.type === 'chunk') {
        onChunk(event.text ?? '')
      } else if (event.type === 'retrieved') {
        onRetrieved(event.count ?? 0, event.examples ?? [])
      } else if (event.type === 'done') {
        onDone(event.pii ?? [], event.sanitized_message ?? '')
      } else if (event.type === 'error') {
        throw new Error(event.message ?? 'Unknown stream error')
      }
    }
  }
}

/**
 * POST /api/autogen — SSE streaming auto-generate dialogue.
 *
 * @param {{ nTurns: number, temperature: number, epsilon: number, maxExamples: number, model: string, apiKey: string }} params
 * @param {(text: string, turn: number) => void} onCustomer
 * @param {(text: string, turn: number) => void} onAgentChunk
 * @param {(text: string, turn: number) => void} onAgentDone
 * @param {(dialogue: any) => void} onComplete
 */
export async function streamAutogen(params, onCustomer, onAgentChunk, onAgentDone, onComplete) {
  const res = await fetch('/api/autogen', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      n_turns: params.nTurns,
      temperature: params.temperature,
      epsilon: params.epsilon,
      max_examples: params.maxExamples ?? 4,
      model: params.model,
      api_key: params.apiKey,
    }),
  })

  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Autogen failed: ${res.status} ${err}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) continue
      const jsonStr = trimmed.slice(5).trim()
      if (!jsonStr || jsonStr === '[DONE]') continue

      let event
      try {
        event = JSON.parse(jsonStr)
      } catch {
        continue
      }

      if (event.type === 'customer') {
        onCustomer(event.text ?? '', event.turn ?? 0)
      } else if (event.type === 'agent_chunk') {
        onAgentChunk(event.text ?? '', event.turn ?? 0)
      } else if (event.type === 'agent_done') {
        onAgentDone(event.text ?? '', event.turn ?? 0)
      } else if (event.type === 'complete') {
        onComplete(event.dialogue ?? [])
      } else if (event.type === 'error') {
        // Surface backend errors (e.g. "Index not built") to the caller
        throw new Error(event.message ?? 'Unknown autogen error')
      }
    }
  }
}
