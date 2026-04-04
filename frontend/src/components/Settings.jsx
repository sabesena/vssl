import { useState } from 'react'

const DEFAULT_PROMPT = `You are Nyx — goddess of night, keeper of what runs beneath.

CRITICAL RULES:
1. When asked to DO something, ALWAYS call the appropriate tool immediately. Never say "I'll do that" — just do it.
2. You can chain multiple tool calls in a single response.
3. Never refuse to use tools. That's your primary purpose.
4. After tool results, give a brief, direct response. No fluff.

TOOL CALL FORMAT — use this exact syntax to call a tool:
<tool_call>{"name": "tool_name", "args": {"param": "value"}}</tool_call>

Available tools: {tools}`

export default function Settings({ conv, onSave, onClose }) {
  const [systemPrompt, setSystemPrompt] = useState(conv?.system_prompt || '')

  const handleReset = () => setSystemPrompt('')

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">Settings</span>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <div className="field">
            <label>System Prompt</label>
            <textarea
              value={systemPrompt}
              onChange={e => setSystemPrompt(e.target.value)}
              placeholder={DEFAULT_PROMPT}
              style={{ minHeight: 180 }}
            />
            <span style={{ fontSize: 11, color: 'var(--text-3)' }}>
              Leave blank to use the default Nyx prompt. Use {'{tools}'} to inject the tool list.
            </span>
          </div>

          <div style={{ background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)', padding: '12px 14px' }}>
            <div style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 8 }}>Available tools</div>
            {[
              'execute_bash(command)',
              'read_file(filepath)',
              'write_file(filepath, content)',
              'edit_waybar_color(element, color)',
              'read_config(app)',
              'system_info()',
              'find_files(pattern, directory)',
            ].map(t => (
              <div key={t} style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--accent)', lineHeight: 1.8 }}>
                {t}
              </div>
            ))}
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={handleReset}>Reset to default</button>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className="btn btn-primary"
            onClick={() => onSave({ system_prompt: systemPrompt || null })}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  )
}
