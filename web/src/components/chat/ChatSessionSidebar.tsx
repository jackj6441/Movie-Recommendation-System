import type { StoredChatSession } from "../../lib/chatSessionStore"
import { CloseIcon, SettingsIcon, SpeechBubbleIcon } from "../icons"
import { SidebarSceneDecor } from "./SidebarSceneDecor"

type ChatSessionSidebarProps = {
  sessions: StoredChatSession[]
  activeSessionId: string | null
  open?: boolean
  onClose?: () => void
  onNewChat: () => void
  onSelectSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
  onJumpToTurn: (turnId: string) => void
}

export function ChatSessionSidebar({
  sessions,
  activeSessionId,
  open = false,
  onClose,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onJumpToTurn,
}: ChatSessionSidebarProps) {
  const active = sessions.find((row) => row.id === activeSessionId)

  const handleSelectSession = (sessionId: string) => {
    onSelectSession(sessionId)
    onClose?.()
  }

  const handleNewChat = () => {
    onNewChat()
    onClose?.()
  }

  const handleJumpToTurn = (turnId: string) => {
    onJumpToTurn(turnId)
    onClose?.()
  }

  return (
    <aside
      className={`chat-session-sidebar${open ? " is-drawer-open" : ""}`}
      aria-label="Chat history"
    >
      <div className="chat-session-sidebar-main">
        <div className="chat-session-sidebar-header">
          <h2 className="chat-session-sidebar-title">Chats</h2>
          <div className="chat-session-sidebar-actions">
            <button type="button" className="chat-session-new-btn" onClick={handleNewChat}>
              New chat
            </button>
            {onClose && (
              <button
                type="button"
                className="chat-session-close-btn"
                aria-label="Close chat history"
                onClick={onClose}
              >
                <CloseIcon size={20} />
              </button>
            )}
          </div>
        </div>

        <ul className="chat-session-list">
          {sessions.map((session) => (
            <li key={session.id} className="chat-session-item">
              <button
                type="button"
                className={`chat-session-link${session.id === activeSessionId ? " is-active" : ""}`}
                onClick={() => handleSelectSession(session.id)}
              >
                <SpeechBubbleIcon className="chat-session-link-icon" size={15} />
                <span className="chat-session-link-text">{session.title}</span>
              </button>
              <button
                type="button"
                className="chat-session-delete-btn"
                aria-label={`Delete ${session.title}`}
                onClick={() => onDeleteSession(session.id)}
              >
                <CloseIcon size={16} />
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
                      onClick={() => handleJumpToTurn(turn.id)}
                    >
                      {turn.content}
                    </button>
                  </li>
                ))}
            </ul>
          </div>
        )}
      </div>

      <div className="chat-session-sidebar-wing-bottom">
        <div className="chat-session-sidebar-footer">
          <button
            type="button"
            className="chat-session-settings-btn"
            aria-label="Settings"
            disabled
            title="Settings (coming soon)"
          >
            <SettingsIcon size={18} />
            <span>Settings</span>
          </button>
        </div>
        <SidebarSceneDecor variant="lamp" />
      </div>
    </aside>
  )
}
