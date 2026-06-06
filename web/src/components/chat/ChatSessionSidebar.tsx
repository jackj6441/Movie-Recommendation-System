import type { StoredChatSession } from "../../lib/chatSessionStore"

type ChatSessionSidebarProps = {
  sessions: StoredChatSession[]
  activeSessionId: string | null
  onNewChat: () => void
  onSelectSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
  onJumpToTurn: (turnId: string) => void
}

export function ChatSessionSidebar({
  sessions,
  activeSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onJumpToTurn,
}: ChatSessionSidebarProps) {
  const active = sessions.find((row) => row.id === activeSessionId)

  return (
    <aside className="chat-session-sidebar" aria-label="Chat history">
      <div className="chat-session-sidebar-header">
        <h2 className="chat-session-sidebar-title">Chats</h2>
        <button type="button" className="chat-session-new-btn" onClick={onNewChat}>
          New chat
        </button>
      </div>

      <ul className="chat-session-list">
        {sessions.map((session) => (
          <li key={session.id} className="chat-session-item">
            <button
              type="button"
              className={`chat-session-link${session.id === activeSessionId ? " is-active" : ""}`}
              onClick={() => onSelectSession(session.id)}
            >
              {session.title}
            </button>
            <button
              type="button"
              className="chat-session-delete-btn"
              aria-label={`Delete ${session.title}`}
              onClick={() => onDeleteSession(session.id)}
            >
              ×
            </button>
          </li>
        ))}
      </ul>

      {active && active.turns.length > 0 && (
        <div className="chat-session-turns">
          <h3 className="chat-session-turns-label">This thread</h3>
          <ul className="chat-session-turn-list">
            {active.turns
              .filter((turn) => turn.role === "user")
              .map((turn) => (
                <li key={turn.id}>
                  <button
                    type="button"
                    className="chat-session-turn-link"
                    onClick={() => onJumpToTurn(turn.id)}
                  >
                    {turn.content}
                  </button>
                </li>
              ))}
          </ul>
        </div>
      )}
    </aside>
  )
}
