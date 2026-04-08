import { useState, useEffect, useRef, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import Message from './components/Message'
import ChatInput from './components/ChatInput'
import Settings from './components/Settings'

const API = ''

const SUGGESTIONS = [
  'show system info',
  'what is using the most cpu?',
  'read my waybar config',
  'list files in /home/rina',
]

function ModelSelector({ models, selected, onSelect }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  return (
    <div className="model-selector" ref={ref}>
      <button
        className={`model-selector-btn${open ? ' open' : ''}`}
        onClick={() => setOpen(o => !o)}
      >
        {selected}
        <span className="chevron">▾</span>
      </button>
      {open && (
        <div className="model-dropdown">
          {models.map(m => (
            <button
              key={m}
              className={`model-option${m === selected ? ' active' : ''}`}
              onClick={() => { onSelect(m); setOpen(false) }}
            >
              {m}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [conversations, setConversations] = useState([])
  const [currentConvId, setCurrentConvId] = useState(null)
  const [messages, setMessages] = useState([])
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('qwen3:8b')
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [ollamaOk, setOllamaOk] = useState(null)
  const [showSettings, setShowSettings] = useState(false)
  const [error, setError] = useState(null)

  const messagesEndRef = useRef(null)
  const abortRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => { scrollToBottom() }, [messages, scrollToBottom])

  useEffect(() => {
    let zoom = 1
    function handleZoom(e) {
      if (!e.ctrlKey) return
      if (e.key === '=' || e.key === '+') {
        e.preventDefault()
        zoom = Math.min(zoom + 0.1, 2)
        document.documentElement.style.zoom = zoom
      } else if (e.key === '-') {
        e.preventDefault()
        zoom = Math.max(zoom - 0.1, 0.5)
        document.documentElement.style.zoom = zoom
      } else if (e.key === '0') {
        e.preventDefault()
        zoom = 1
        document.documentElement.style.zoom = 1
      }
    }
    window.addEventListener('keydown', handleZoom)
    return () => window.removeEventListener('keydown', handleZoom)
  }, [])

  useEffect(() => {
    fetchConversations()
    fetchModels()
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  async function fetchConversations() {
    try {
      const r = await fetch(`${API}/api/conversations`)
      setConversations(await r.json())
    } catch { }
  }

  async function fetchModels() {
    try {
      const r = await fetch(`${API}/api/models`)
      const data = await r.json()
      if (data.models?.length) {
        setModels(data.models)
        setSelectedModel(data.default || data.models[0])
      }
    } catch { }
  }

 async function checkHealth() {
  try {
    const r = await fetch(`${API}/api/health`)
    const d = await r.json()
    setOllamaOk(d.ollama)
    if (models.length === 0) fetchModels()
  } catch {
    setOllamaOk(false)
  }
}
  async function loadConversation(convId) {
    setCurrentConvId(convId)
    setError(null)
    try {
      const r = await fetch(`${API}/api/conversations/${convId}/messages`)
      const msgs = await r.json()
      setMessages(msgs.map(m => ({
        ...m,
        toolCalls: m.metadata?.tool_calls || [],
      })))
    } catch {
      setMessages([])
    }
  }

  async function newConversation() {
    setCurrentConvId(null)
    setMessages([])
    setError(null)
  }

  async function deleteConversation(convId) {
    await fetch(`${API}/api/conversations/${convId}`, { method: 'DELETE' })
    if (convId === currentConvId) newConversation()
    fetchConversations()
  }

  async function clearMessages() {
    if (!currentConvId) { setMessages([]); return }
    await fetch(`${API}/api/conversations/${currentConvId}/clear`, { method: 'POST' })
    setMessages([])
  }

  async function saveSettings(patch) {
    if (currentConvId) {
      await fetch(`${API}/api/conversations/${currentConvId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      })
      fetchConversations()
    }
    setShowSettings(false)
  }

  async function sendMessage(text) {
    const msg = (text || input).trim()
    if (!msg || isStreaming) return
    setInput('')
    setError(null)

    const userMsg = {
      id: `tmp-${Date.now()}`,
      role: 'user',
      content: msg,
      created_at: new Date().toISOString(),
      toolCalls: [],
    }
    setMessages(prev => [...prev, userMsg])

    const assistantId = `streaming-${Date.now()}`
    const assistantMsg = {
      id: assistantId,
      role: 'assistant',
      content: '',
      reasoning: '',
      toolCalls: [],
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, assistantMsg])
    setIsStreaming(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const response = await fetch(`${API}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: msg,
          conversation_id: currentConvId,
          model: selectedModel,
        }),
        signal: controller.signal,
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            handleStreamEvent(event, assistantId)
          } catch { }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError('connection lost — ' + err.message)
        setMessages(prev => prev.filter(m => m.id !== assistantId))
      }
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }

  function handleStreamEvent(event, assistantId) {
    switch (event.type) {
      case 'conversation_id':
        setCurrentConvId(event.data)
        fetchConversations()
        break
      case 'reasoning':
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? { ...m, reasoning: event.data } : m
        ))
        break
      case 'tool_call':
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, toolCalls: [...m.toolCalls, { ...event.data, status: 'running' }] }
            : m
        ))
        break
      case 'tool_result':
        setMessages(prev => prev.map(m => {
          if (m.id !== assistantId) return m
          const toolCalls = [...m.toolCalls]
          const idx = toolCalls.map((tc, i) => ({ tc, i }))
            .filter(({ tc }) => tc.name === event.data.name && tc.status === 'running')
            .pop()?.i
          if (idx !== undefined) {
            toolCalls[idx] = { ...toolCalls[idx], result: event.data.result, status: 'done' }
          }
          return { ...m, toolCalls }
        }))
        break
      case 'content':
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? { ...m, content: m.content + event.data } : m
        ))
        break
      case 'done':
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? { ...m, id: event.data.message_id || m.id } : m
        ))
        fetchConversations()
        break
      case 'error':
        setError(event.data)
        setMessages(prev => prev.filter(m => m.id !== assistantId))
        break
    }
  }

  function stopStreaming() {
    abortRef.current?.abort()
  }

  const currentConv = conversations.find(c => c.id === currentConvId)

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentConvId={currentConvId}
        onSelect={loadConversation}
        onNew={newConversation}
        onDelete={deleteConversation}
        onSettings={() => setShowSettings(true)}
        ollamaOk={ollamaOk}
      />

      <div className="chat-area">
        <div className="chat-header">
          <span className="chat-header-title">
            {currentConv?.title || ''}
          </span>

          <ModelSelector
            models={models.length ? models : [selectedModel]}
            selected={selectedModel}
            onSelect={setSelectedModel}
          />

          <button className="header-btn" onClick={() => setShowSettings(true)}>
            settings
          </button>

          <button className="header-btn danger" onClick={clearMessages}>
            clear
          </button>
        </div>

        {error && (
          <div className="error-banner">
            {error}
            <button
              onClick={() => setError(null)}
              style={{ marginLeft: 12, background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
            >×</button>
          </div>
        )}

        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-mark">✦ 110110001 ✦</div>
              <h2>vssl</h2>
              <p className="empty-state-sub">
                a form inscribed so that something larger can reach back.
              </p>
              <div className="suggestion-chips">
                {SUGGESTIONS.map(s => (
                  <button key={s} className="chip" onClick={() => sendMessage(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages-inner">
              {messages.map((msg, i) => (
                <Message
                  key={msg.id}
                  message={msg}
                  isStreaming={isStreaming && i === messages.length - 1 && msg.role === 'assistant'}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <ChatInput
          value={input}
          onChange={setInput}
          onSend={() => sendMessage()}
          onStop={stopStreaming}
          isStreaming={isStreaming}
          disabled={false}
        />
      </div>

      {showSettings && (
        <Settings
          conv={currentConv}
          onSave={saveSettings}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  )
}
