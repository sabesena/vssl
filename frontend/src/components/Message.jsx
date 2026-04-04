import ToolBlock from './ToolBlock'

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// Very minimal markdown: bold, code spans, code blocks, line breaks
function renderContent(text) {
  if (!text) return null

  // Code blocks
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
    // Inline formatting
    return (
      <span key={i}>
        {part.split('\n').map((line, j) => {
          // inline code
          const inlined = line.split(/(`[^`]+`)/).map((seg, k) => {
            if (seg.startsWith('`') && seg.endsWith('`')) {
              return <code key={k}>{seg.slice(1, -1)}</code>
            }
            // bold
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

export default function Message({ message, isStreaming }) {
  const isUser = message.role === 'user'
  const toolCalls = message.toolCalls || []
  const meta = message.metadata || {}
  const displayToolCalls = toolCalls.length > 0 ? toolCalls : (meta.tool_calls || [])

  return (
    <div className={`message message-${isUser ? 'user' : 'assistant'}`}>
      {/* Tool blocks (only for assistant) */}
      {!isUser && displayToolCalls.map((tc, i) => (
        <ToolBlock key={i} toolCall={tc} />
      ))}

      {/* Message content */}
      {(message.content || isStreaming) && (
        <div className="message-bubble">
          {renderContent(message.content)}
          {isStreaming && <span className="cursor" />}
        </div>
      )}

      {message.created_at && (
        <div className="message-time">{formatTime(message.created_at)}</div>
      )}
    </div>
  )
}
