import { useState } from 'react'

export default function ToolBlock({ toolCall }) {
  const [expanded, setExpanded] = useState(true)
  const { name, args, result, status } = toolCall

  const isRunning = status === 'running'
  const isError = result?.status === 'error'
  const isConfirm = result?.status === 'confirmation_required'

  const statusIcon = isRunning ? '⏳' : isError ? '✗' : isConfirm ? '⚠️' : '✓'
  const argsPreview = Object.entries(args || {})
    .map(([k, v]) => `${k}=${JSON.stringify(v).slice(0, 40)}`)
    .join(', ')

  const outputText = result?.output || (result ? JSON.stringify(result, null, 2) : '')
  const outputClass = isError ? 'error' : isConfirm ? 'warning' : 'success'

  return (
    <div className="tool-block">
      <button className="tool-header" onClick={() => setExpanded(e => !e)}>
        <span className="tool-status-icon">{statusIcon}</span>
        <span className="tool-name">{name}</span>
        {argsPreview && <span className="tool-args-preview">({argsPreview})</span>}
        <span className="tool-chevron">{expanded ? '▾' : '▸'}</span>
      </button>

      {expanded && (
        <div className="tool-body">
          {args && Object.keys(args).length > 0 && (
            <div className="tool-args-section">
              <div className="tool-section-label">Arguments</div>
              <table className="tool-args-table">
                <tbody>
                  {Object.entries(args).map(([k, v]) => (
                    <tr key={k}>
                      <td className="tool-arg-key">{k}</td>
                      <td className="tool-arg-val">
                        {typeof v === 'string' ? v : JSON.stringify(v)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {isRunning ? (
            <div className="tool-running">
              <div className="spinner" />
              <span>Running...</span>
            </div>
          ) : outputText ? (
            <>
              <div className="tool-section-label">Output</div>
              <pre className={`tool-output ${outputClass}`}>{outputText}</pre>
            </>
          ) : null}
        </div>
      )}
    </div>
  )
}
