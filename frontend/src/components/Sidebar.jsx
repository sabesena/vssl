function groupByDate(convs) {
  const today = new Date().toDateString()
  const yesterday = new Date(Date.now() - 86400000).toDateString()
  const groups = { Today: [], Yesterday: [], Older: [] }
  for (const c of convs) {
    const d = new Date(c.updated_at).toDateString()
    if (d === today) groups.Today.push(c)
    else if (d === yesterday) groups.Yesterday.push(c)
    else groups.Older.push(c)
  }
  return groups
}

export default function Sidebar({
  conversations,
  currentConvId,
  onSelect,
  onNew,
  onDelete,
  onSettings,
  ollamaOk,
}) {
  const groups = groupByDate(conversations)

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-logo">
          vssl <span className="sigil">✦</span>
        </span>
        <div
          className={`status-dot ${ollamaOk ? 'ok' : 'err'}`}
          title={ollamaOk ? 'nyx is listening' : 'ollama unreachable'}
        />
      </div>

      <button className="new-chat-btn" onClick={onNew}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        new invocation
      </button>

      <div className="conv-list">
        {Object.entries(groups).map(([label, convs]) =>
          convs.length === 0 ? null : (
            <div key={label}>
              <div className="conv-group-label">{label}</div>
              {convs.map(conv => (
                <div
                  key={conv.id}
                  className={`conv-item ${conv.id === currentConvId ? 'active' : ''}`}
                  onClick={() => onSelect(conv.id)}
                >
                  <span className="conv-item-title">{conv.title || 'new conversation'}</span>
                  <button
                    className="conv-delete-btn"
                    title="delete"
                    onClick={e => { e.stopPropagation(); onDelete(conv.id) }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )
        )}

        {conversations.length === 0 && (
          <div style={{ padding: '24px 10px', color: 'var(--text-4)', fontSize: 11, textAlign: 'center', fontStyle: 'italic', fontFamily: 'var(--font-serif)' }}>
            no conversations yet
          </div>
        )}
      </div>

      <div className="sidebar-footer">
        <button className="settings-btn" onClick={onSettings}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          settings
        </button>
      </div>
    </div>
  )
}
