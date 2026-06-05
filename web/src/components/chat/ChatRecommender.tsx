import { useCallback, useId, useState } from "react"
import { postRagChat } from "../../api/ragChat"
import { MAX_GENRES } from "../../config"
import { buildUserTurnContent, canSendChatTurn } from "../../lib/chatUserTurn"
import { scrollLatestAssistantBubble } from "../../lib/scrollLatestAssistant"
import { useGenres } from "../../hooks/useGenres"
import type { ChatTurn } from "../../types"
import type { RagChatContext } from "../../types"
import { ChatThread } from "./ChatThread"
import { GenreChipsRow } from "./GenreChipsRow"
import { TasteRail } from "./TasteRail"
import { TasteRailCompact } from "./TasteRailCompact"

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
  const sessionContext = turns.findLast((turn) => turn.final)?.final?.context
  const hasSessionSeeds = (sessionContext?.seeds.length ?? 0) > 0
  const sendEnabled = canSendChatTurn(message, selectedGenres, {
    chatLoading,
    hasSessionSeeds,
  })

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

  const runChatTurn = async (options: {
    message: string
    userContent: string
    genres?: string[]
    seed_movie_ids?: number[]
    seed_update_mode?: "append" | "replace"
    reset_context?: boolean
    clear_year_bounds?: boolean
    scrollToLatestAssistant?: boolean
  }) => {
    const userTurn: ChatTurn = {
      id: newTurnId(),
      role: "user",
      content: options.userContent,
    }
    const assistantId = newTurnId()
    setTurns((prev) => [
      ...prev,
      userTurn,
      { id: assistantId, role: "assistant", content: "", streaming: true },
    ])
    setChatLoading(true)
    setChatError(null)

    try {
      const result = await postRagChat({
        session_id: sessionId,
        message: options.message,
        genres: options.genres ?? selectedGenres,
        seed_movie_ids: options.seed_movie_ids,
        seed_update_mode: options.seed_update_mode,
        reset_context: options.reset_context,
        clear_year_bounds: options.clear_year_bounds,
      })
      setSessionId(result.final.session_id)
      setSelectedGenres(result.final.context.genres)
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
      if (options.scrollToLatestAssistant) {
        requestAnimationFrame(() => scrollLatestAssistantBubble())
      }
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Unknown error")
      setTurns((prev) => prev.filter((turn) => turn.id !== assistantId))
    } finally {
      setChatLoading(false)
    }
  }

  const sendMessage = async () => {
    if (!sendEnabled) return

    const trimmed = message.trim()
    const userContent = buildUserTurnContent(trimmed, selectedGenres, {
      hasSessionSeeds,
    })
    if (!userContent) return

    setMessage("")
    await runChatTurn({ message: trimmed, userContent })
  }

  const activeContext: RagChatContext | undefined = sessionContext

  const removeSeed = async (movieId: number, title: string) => {
    if (!activeContext) return
    const remaining = activeContext.seeds
      .filter((seed) => seed.movie_id !== movieId)
      .map((seed) => seed.movie_id)
    await runChatTurn({
      message: "",
      userContent: `Removed ${title} from seeds.`,
      genres: activeContext.genres,
      seed_movie_ids: remaining,
      seed_update_mode: "replace",
    })
  }

  const removeGenre = async (genre: string) => {
    if (!activeContext) return
    const remaining = activeContext.genres.filter((name) => name !== genre)
    setSelectedGenres(remaining)
    await runChatTurn({
      message: "",
      userContent: `Removed ${genre} from your taste.`,
      genres: remaining,
      seed_movie_ids: activeContext.seeds.map((seed) => seed.movie_id),
      seed_update_mode: "replace",
    })
  }

  const removeYear = async () => {
    if (!activeContext) return
    await runChatTurn({
      message: "",
      userContent: "Removed year filter.",
      genres: activeContext.genres,
      seed_movie_ids: activeContext.seeds.map((seed) => seed.movie_id),
      seed_update_mode: "replace",
      clear_year_bounds: true,
    })
  }

  const startOver = async () => {
    if (chatLoading) return
    if (sessionId) {
      setChatLoading(true)
      try {
        await postRagChat({
          session_id: sessionId,
          message: "",
          genres: [],
          reset_context: true,
        })
      } catch {
        setChatError("Couldn't reset your session. Try again.")
        setChatLoading(false)
        return
      }
    }
    resetChat()
    setChatLoading(false)
  }

  const moreLikeThis = async (movieId: number, title: string) => {
    await runChatTurn({
      message: "",
      userContent: `More like: ${title}`,
      seed_movie_ids: [movieId],
      seed_update_mode: "append",
      scrollToLatestAssistant: true,
    })
  }

  const submitDisambiguation = async (movieIds: number[]) => {
    const lastAssistant = [...turns]
      .reverse()
      .find((turn) => turn.role === "assistant" && turn.final?.disambiguation_candidates)
    const candidates = lastAssistant?.final?.disambiguation_candidates ?? []
    const titles = movieIds.map(
      (id) => candidates.find((row) => row.movie_id === id)?.title ?? `Movie ${id}`
    )
    await runChatTurn({
      message: "",
      userContent: `You picked: ${titles.join(", ")}`,
      seed_movie_ids: movieIds,
      seed_update_mode: "replace",
    })
  }

  const onComposerKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      void sendMessage()
    }
  }

  const tasteHandlers = activeContext
    ? {
        onRemoveSeed: (id: number, title: string) => void removeSeed(id, title),
        onRemoveGenre: (genre: string) => void removeGenre(genre),
        onRemoveYear: () => void removeYear(),
      }
    : null

  return (
    <section
      className={`chat-layout${hasThread && activeContext ? " chat-layout--with-rail" : ""}`}
    >
      <div className={`chat-panel${hasThread ? " chat-panel--thread" : " chat-panel--home"}`}>
        {!hasThread && (
          <header className="chat-home-header">
            <h2 className="chat-greeting">What are you in the mood to watch?</h2>
            <p className="chat-lead">
              Pick up to three genres, describe a vibe or a favorite movie, and get recommendations.
            </p>
          </header>
        )}

        {hasThread && (
          <ChatThread
            turns={turns}
            onNewChat={() => void startOver()}
            onMoreLike={(id, title) => void moreLikeThis(id, title)}
            onDisambiguationSubmit={(ids) => void submitDisambiguation(ids)}
            pickerDisabled={chatLoading}
            moreLikeDisabled={chatLoading}
          />
        )}

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

        {hasThread && activeContext && tasteHandlers && (
          <TasteRailCompact
            context={activeContext}
            disabled={chatLoading}
            {...tasteHandlers}
          />
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
              disabled={!sendEnabled}
              onClick={() => void sendMessage()}
            >
              {chatLoading ? "Thinking…" : "Send"}
            </button>
            {hasThread && (
              <button type="button" className="ghost" onClick={() => void startOver()} disabled={chatLoading}>
                Start over
              </button>
            )}
          </div>
        </div>
      </div>

      {hasThread && activeContext && tasteHandlers && (
        <TasteRail
          className="taste-rail--desktop"
          context={activeContext}
          disabled={chatLoading}
          {...tasteHandlers}
        />
      )}
    </section>
  )
}
