import { useCallback, useId, useState } from "react"
import { postRagChat } from "../../api/ragChat"
import { MAX_GENRES } from "../../config"
import { useGenres } from "../../hooks/useGenres"
import type { ChatTurn } from "../../types"
import { ChatThread } from "./ChatThread"
import { GenreChipsRow } from "./GenreChipsRow"

function newTurnId(): string {
  return `turn-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function ChatRecommender() {
  const { genres, loading: genresLoading, error: genresError, retry: retryGenres } = useGenres()
  const [selectedGenres, setSelectedGenres] = useState<string[]>([])
  const [message, setMessage] = useState("")
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const composerId = useId()

  const hasThread = turns.length > 0

  const toggleGenre = (genre: string) => {
    setSelectedGenres((prev) => {
      if (prev.includes(genre)) {
        return prev.filter((g) => g !== genre)
      }
      if (prev.length >= MAX_GENRES) return prev
      return [...prev, genre]
    })
  }

  const resetChat = useCallback(() => {
    setSessionId(null)
    setTurns([])
    setMessage("")
    setSelectedGenres([])
    setChatError(null)
  }, [])

  const sendMessage = async () => {
    const trimmed = message.trim()
    if (!trimmed || chatLoading) return

    const userTurn: ChatTurn = {
      id: newTurnId(),
      role: "user",
      content: trimmed,
    }
    const assistantId = newTurnId()
    setTurns((prev) => [
      ...prev,
      userTurn,
      { id: assistantId, role: "assistant", content: "", streaming: true },
    ])
    setMessage("")
    setChatLoading(true)
    setChatError(null)

    try {
      const result = await postRagChat({
        session_id: sessionId,
        message: trimmed,
        genres: selectedGenres,
      })
      setSessionId(result.final.session_id)
      setTurns((prev) =>
        prev.map((turn) =>
          turn.id === assistantId
            ? {
                ...turn,
                content: result.assistantMessage,
                streaming: false,
                final: result.final,
              }
            : turn
        )
      )
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Unknown error")
      setTurns((prev) => prev.filter((turn) => turn.id !== assistantId))
    } finally {
      setChatLoading(false)
    }
  }

  const onComposerKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      void sendMessage()
    }
  }

  return (
    <section className="chat-layout">
      <div className={`chat-panel${hasThread ? " chat-panel--thread" : " chat-panel--home"}`}>
        {!hasThread && (
          <header className="chat-home-header">
            <h2 className="chat-greeting">What are you in the mood to watch?</h2>
            <p className="chat-lead">
              Pick up to three genres, describe a vibe or a favorite movie, and get recommendations.
            </p>
          </header>
        )}

        {hasThread && <ChatThread turns={turns} onNewChat={resetChat} />}

        {chatError && (
          <div className="chat-error" role="alert">
            <p>Couldn&apos;t complete that request. Check your connection and try again.</p>
            <button type="button" className="retry-btn" onClick={() => setChatError(null)}>
              Dismiss
            </button>
          </div>
        )}

        {genresError && (
          <div className="genre-error" role="alert">
            <p>{genresError}</p>
            <button type="button" className="retry-btn" onClick={retryGenres}>
              Retry genres
            </button>
          </div>
        )}

        <div className="chat-composer-wrap">
          <label className="sr-only" htmlFor={composerId}>
            Message
          </label>
          <textarea
            id={composerId}
            className="chat-composer-input"
            rows={hasThread ? 2 : 3}
            placeholder="Describe the kind of movies you want…"
            value={message}
            disabled={chatLoading}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={onComposerKeyDown}
          />
          <GenreChipsRow
            genres={genres}
            selected={selectedGenres}
            loading={genresLoading}
            disabled={chatLoading}
            onToggle={toggleGenre}
          />
          <div className="chat-composer-actions">
            <button
              type="button"
              className="chat-send-btn"
              disabled={chatLoading || !message.trim()}
              onClick={() => void sendMessage()}
            >
              {chatLoading ? "Thinking…" : "Send"}
            </button>
            {hasThread && (
              <button type="button" className="ghost" onClick={resetChat} disabled={chatLoading}>
                New chat
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
