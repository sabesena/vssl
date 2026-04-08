import { useState } from 'react'
import ToolBlock from './ToolBlock'

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function renderContent(text) {
  if (!text) return null
  const parts = text.split(/(```[\s\S]*?```)/g)
  return parts.map((part, i) => {
    if (part.startsWith('```')) {
      const lines = part.slice(3, -3).split('\n')
      const lang = lines[0].trim()
      const code = lines.slice(lang ? 1 : 0).join('\n')
      return (
        <pre key={i} style={{ margin: '8px 0' }}>
          <code>{code || lang}</code>
        </pre>
      )
    }
    return (
      <span key={i}>
        {part.split('\n').map((line, j) => {
          const inlined = line.split(/(`[^`]+`)/).map((seg, k) => {
            if (seg.startsWith('`') && seg.endsWith('`')) {
              return <code key={k}>{seg.slice(1, -1)}</code>
            }
            return seg.split(/(\*\*[^*]+\*\*)/).map((s, m) => {
              if (s.startsWith('**') && s.endsWith('**')) {
                return <strong key={m}>{s.slice(2, -2)}</strong>
              }
              return s
            })
          })
          return (
            <span key={j}>
              {inlined}
              {j < part.split('\n').length - 1 && <br />}
            </span>
          )
        })}
      </span>
    )
  })
}

function TraceDrawer({ reasoning, toolCalls }) {
  const [open, setOpen] = useState(false)
  const hasTrace = reasoning || toolCalls.length > 0
  if (!hasTrace) return null

  return (
    <div className="trace-drawer">
      <button
        className={`trace-toggle${open ? ' open' : ''}`}
        onClick={() => setOpen(o => !o)}
      >
        <span className="trace-sigil">✦</span>
        invocation trace
        <span className="trace-chevron">▾</span>
      </button>

      {open && (
        <div className="trace-body">
          {reasoning && (
            <div className="trace-section">
              <div className="trace-label">reasoning</div>
              <div className="trace-reasoning">{reasoning}</div>
            </div>
          )}
          {toolCalls.map((tc, i) => (
            <div key={i} className="trace-section">
              <div className="trace-label">tool · {tc.name}</div>
              {tc.args && Object.keys(tc.args).length > 0 && (
                <div className="trace-block">
                  <div className="trace-sublabel">args</div>
                  <pre className="trace-pre">
                    {JSON.stringify(tc.args, null, 2)}
                  </pre>
                </div>
              )}
              {tc.result && (
                <div className="trace-block">
                  <div className="trace-sublabel">output</div>
                  <pre className="trace-pre">
                    {typeof tc.result === 'string'
                      ? tc.result
                      : tc.result.output || JSON.stringify(tc.result, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Message({ message, isStreaming }) {
  const isUser = message.role === 'user'
  const toolCalls = message.toolCalls || []
  const meta = message.metadata || {}
  const displayToolCalls = toolCalls.length > 0 ? toolCalls : (meta.tool_calls || [])
  const reasoning = message.reasoning || meta.reasoning || ''

  return (
    <div className={`message message-${isUser ? 'user' : 'assistant'}`}>
      {!isUser && displayToolCalls.map((tc, i) => (
        <ToolBlock key={i} toolCall={tc} />
      ))}

      {(message.content || isStreaming) && (
        <div className="message-bubble">
          {renderContent(message.content)}
          {isStreaming && <span className="cursor" />}
        </div>
      )}

      {!isUser && !isStreaming && (
        <TraceDrawer reasoning={reasoning} toolCalls={displayToolCalls} />
      )}

      {message.created_at && (
        <div className="message-time">{formatTime(message.created_at)}</div>
      )}
    </div>
  )
}
