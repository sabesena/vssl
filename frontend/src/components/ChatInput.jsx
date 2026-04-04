import { useRef, useEffect } from 'react'

export default function ChatInput({ value, onChange, onSend, onStop, isStreaming, disabled }) {
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 180) + 'px'
  }, [value])

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!isStreaming && value.trim()) onSend()
    }
  }

  return (
    <div className="input-area">
      <div className="input-wrapper">
        <textarea
          ref={ref}
          className="chat-textarea"
          placeholder="speak your plea..."
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={handleKey}
          rows={1}
          disabled={disabled}
        />
        {isStreaming ? (
          <button className="send-btn stop" onClick={onStop} title="stop">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <rect x="4" y="4" width="16" height="16" rx="1" />
            </svg>
          </button>
        ) : (
          <button
            className="send-btn"
            onClick={onSend}
            disabled={!value.trim()}
            title="invoke"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        )}
      </div>
      <div className="input-hint">the vessel can act on your machine</div>
    </div>
  )
}
