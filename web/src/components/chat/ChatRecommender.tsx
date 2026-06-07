import { useCallback, useEffect, useId, useRef, useState } from "react"
import { postRagChat } from "../../api/ragChat"
import { MAX_GENRES, MAX_SEEDS } from "../../config"
import {
  createChatSession,
  deleteChatSession,
  deriveSessionTitle,
  loadActiveSessionId,
  loadChatSessions,
  saveActiveSessionId,
  upsertChatSession,
  type StoredChatSession,
} from "../../lib/chatSessionStore"
import { buildUserTurnContent, canSendChatTurn } from "../../lib/chatUserTurn"
import { scrollLatestAssistantBubble, scrollToTurn } from "../../lib/scrollLatestAssistant"
import {
  formatYearRangeLabel,
  sliderValuesToApi,
} from "../../lib/tasteYear"
import { useGenres } from "../../hooks/useGenres"
import type { ChatTurn } from "../../types"
import type { RagChatContext } from "../../types"
import { ChatSessionSidebar } from "./ChatSessionSidebar"
import { ChatThread } from "./ChatThread"
import { GenreChipsRow } from "./GenreChipsRow"
import { TasteRail } from "./TasteRail"
import { TasteRailCompact } from "./TasteRailCompact"

function newTurnId(): string {
  return `turn-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function ChatRecommender() {
  const { genres, loading: genresLoading, error: genresError, retry: retryGenres } = useGenres()
  const [storedSessions, setStoredSessions] = useState<StoredChatSession[]>([])
  const [localSessionId, setLocalSessionId] = useState<string | null>(null)
  const [selectedGenres, setSelectedGenres] = useState<string[]>([])
  const [message, setMessage] = useState("")
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const [sessionDrawerOpen, setSessionDrawerOpen] = useState(false)
  const composerId = useId()
  const hydratedRef = useRef(false)

  useEffect(() => {
    if (hydratedRef.current) return
    hydratedRef.current = true

    let sessions = loadChatSessions()
    let activeId = loadActiveSessionId()
    if (sessions.length === 0) {
      const created = createChatSession()
      sessions = [created]
      activeId = created.id
    }
    if (!activeId) {
      activeId = sessions[0]?.id ?? null
      if (activeId) {
        saveActiveSessionId(activeId)
      }
    }
    const active = sessions.find((row) => row.id === activeId) ?? sessions[0]
    setStoredSessions(sessions)
    if (active) {
      setLocalSessionId(active.id)
      setSessionId(active.apiSessionId)
      setTurns(active.turns)
      if (active.turns.length > 0) {
        const activeGenres =
          active.turns.findLast((turn) => turn.view)?.view?.context.genres ?? []
        setSelectedGenres(activeGenres)
      }
    }
  }, [])

  const persistActiveSession = useCallback(
    (nextTurns: ChatTurn[], apiSessionId: string | null) => {
      if (!localSessionId) return
      const next: StoredChatSession = {
        id: localSessionId,
        apiSessionId,
        title: deriveSessionTitle(nextTurns),
        turns: nextTurns,
        updatedAt: Date.now(),
      }
      upsertChatSession(next)
      setStoredSessions(loadChatSessions())
    },
    [localSessionId]
  )

  const hasThread = turns.length > 0
  const sessionContext = turns.findLast((turn) => turn.view)?.view?.context
  const hasSessionSeeds = (sessionContext?.seeds.length ?? 0) > 0
  const hasSessionGenres = (sessionContext?.genres.length ?? 0) > 0
  const composerGenres = hasThread ? [] : selectedGenres
  const sendEnabled = canSendChatTurn(message, composerGenres, {
    chatLoading,
    hasSessionSeeds,
    hasSessionGenres,
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

  const resetComposer = useCallback(() => {
    setMessage("")
    setSelectedGenres([])
    setChatError(null)
  }, [])

  const resolveGenresForRequest = (explicit?: string[]) => {
    if (explicit !== undefined) return explicit
    if (hasThread) return []
    return selectedGenres
  }

  const runChatTurn = async (options: {
    message: string
    userContent: string
    genres?: string[]
    seed_movie_ids?: number[]
    seed_update_mode?: "append" | "replace"
    reset_context?: boolean
    clear_year_bounds?: boolean
    year_min?: number | null
    year_max?: number | null
    disambiguation_genre?: string
    /** When false, skip post-turn scroll (default: scroll to latest assistant). */
    scrollToLatestAssistant?: boolean
  }) => {
    const userTurn: ChatTurn = {
      id: newTurnId(),
      role: "user",
      content: options.userContent,
    }
    const assistantId = newTurnId()
    const pendingTurns: ChatTurn[] = [
      ...turns,
      userTurn,
      { id: assistantId, role: "assistant", content: "", streaming: true },
    ]
    setTurns(pendingTurns)
    setChatLoading(true)
    setChatError(null)

    try {
      const result = await postRagChat({
        session_id: sessionId,
        message: options.message,
        genres: resolveGenresForRequest(options.genres),
        seed_movie_ids: options.seed_movie_ids,
        seed_update_mode: options.seed_update_mode,
        reset_context: options.reset_context,
        clear_year_bounds: options.clear_year_bounds,
        year_min: options.year_min,
        year_max: options.year_max,
        disambiguation_genre: options.disambiguation_genre,
      })
      const apiSessionId = result.view.sessionId
      setSessionId(apiSessionId)
      const nextGenres = result.view.context.genres
      setSelectedGenres(nextGenres)
      const nextTurns = pendingTurns.map((turn) =>
        turn.id === assistantId
          ? {
              ...turn,
              content: result.assistantMessage,
              streaming: false,
              view: result.view,
            }
          : turn
      )
      setTurns(nextTurns)
      persistActiveSession(nextTurns, apiSessionId)

      if (options.scrollToLatestAssistant !== false) {
        scrollLatestAssistantBubble()
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
    const userContent = buildUserTurnContent(trimmed, composerGenres, {
      hasSessionSeeds,
      hasSessionGenres,
    })
    if (!userContent) return

    setMessage("")
    await runChatTurn({
      message: trimmed,
      userContent,
      genres: composerGenres,
    })
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

  const toggleGenreInRail = async (genre: string) => {
    if (!activeContext) return
    const current = activeContext.genres
    const updated = current.includes(genre)
      ? current.filter((name) => name !== genre)
      : current.length >= MAX_GENRES
        ? current
        : [...current, genre]
    if (
      updated.length === current.length &&
      updated.every((name, index) => name === current[index])
    ) {
      return
    }
    setSelectedGenres(updated)
    const added = updated.includes(genre) && !current.includes(genre)
    await runChatTurn({
      message: "",
      userContent: added ? `Added ${genre}.` : `Removed ${genre} from your taste.`,
      genres: updated,
      seed_movie_ids: activeContext.seeds.map((seed) => seed.movie_id),
      seed_update_mode: "replace",
    })
  }

  const setYearRange = async (min: number, max: number) => {
    if (!activeContext) return
    const { year_min, year_max } = sliderValuesToApi(min, max)
    await runChatTurn({
      message: "",
      userContent: `Year range: ${formatYearRangeLabel(year_min, year_max)}.`,
      genres: activeContext.genres,
      seed_movie_ids: activeContext.seeds.map((seed) => seed.movie_id),
      seed_update_mode: "replace",
      year_min,
      year_max,
    })
  }

  const setAnyYear = async () => {
    if (!activeContext) return
    await runChatTurn({
      message: "",
      userContent: "Any year.",
      genres: activeContext.genres,
      seed_movie_ids: activeContext.seeds.map((seed) => seed.movie_id),
      seed_update_mode: "replace",
      clear_year_bounds: true,
    })
  }

  const startNewLocalChat = () => {
    const session = createChatSession()
    setStoredSessions(loadChatSessions())
    setLocalSessionId(session.id)
    setSessionId(null)
    setTurns([])
    resetComposer()
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
    setSessionId(null)
    setTurns([])
    resetComposer()
    if (localSessionId) {
      upsertChatSession({
        id: localSessionId,
        apiSessionId: null,
        title: "New chat",
        turns: [],
        updatedAt: Date.now(),
      })
      setStoredSessions(loadChatSessions())
    }
    setChatLoading(false)
  }

  const selectSession = (id: string) => {
    const session = storedSessions.find((row) => row.id === id)
    if (!session) return
    saveActiveSessionId(id)
    setLocalSessionId(id)
    setSessionId(session.apiSessionId)
    setTurns(session.turns)
    const activeGenres =
      session.turns.findLast((turn) => turn.view)?.view?.context.genres ?? []
    setSelectedGenres(activeGenres)
    resetComposer()
  }

  const removeSession = (id: string) => {
    const fallback = deleteChatSession(id)
    const sessions = loadChatSessions()
    setStoredSessions(sessions)
    if (localSessionId === id) {
      if (fallback) {
        selectSession(fallback.id)
      } else {
        startNewLocalChat()
      }
    }
  }

  const addSeedFromRecommendation = async (movieId: number, title: string) => {
    if (!activeContext) return
    const seedIds = activeContext.seeds.map((seed) => seed.movie_id)
    if (seedIds.includes(movieId) || seedIds.length >= MAX_SEEDS) return
    await runChatTurn({
      message: "",
      userContent: `Added ${title}`,
      seed_movie_ids: [movieId],
      seed_update_mode: "append",
    })
  }

  const submitDisambiguation = async (movieIds: number[]) => {
    const lastAssistant = [...turns]
      .reverse()
      .find((turn) => turn.role === "assistant" && turn.view?.disambiguation)
    const candidates = lastAssistant?.view?.disambiguation?.candidates ?? []
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

  const submitDisambiguationGenre = async (genre: string) => {
    await runChatTurn({
      message: "",
      userContent: `You selected: ${genre} (genre)`,
      disambiguation_genre: genre,
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
        onToggleGenre: (genre: string) => void toggleGenreInRail(genre),
        onSetYearRange: (min: number, max: number) => void setYearRange(min, max),
        onSetAnyYear: () => void setAnyYear(),
        genresLoading,
      }
    : null

  return (
    <div className="chat-app-layout">
      {sessionDrawerOpen && (
        <button
          type="button"
          className="chat-drawer-backdrop"
          aria-label="Close chat history"
          onClick={() => setSessionDrawerOpen(false)}
        />
      )}
      <ChatSessionSidebar
        sessions={storedSessions}
        activeSessionId={localSessionId}
        open={sessionDrawerOpen}
        onClose={() => setSessionDrawerOpen(false)}
        onNewChat={startNewLocalChat}
        onSelectSession={selectSession}
        onDeleteSession={removeSession}
        onJumpToTurn={(turnId) => scrollToTurn(turnId)}
      />

      <section
        className={`chat-layout${hasThread && activeContext ? " chat-layout--with-rail" : ""}`}
      >
        <div className={`chat-panel${hasThread ? " chat-panel--thread" : " chat-panel--home"}`}>
          {hasThread && (
            <div className="chat-panel-head">
              <button
                type="button"
                className="chat-chats-toggle"
                onClick={() => setSessionDrawerOpen(true)}
              >
                Chats
              </button>
            </div>
          )}

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
              seedMovieIds={activeContext?.seeds.map((seed) => seed.movie_id) ?? []}
              onAddSeed={(id, title) => void addSeedFromRecommendation(id, title)}
              onDisambiguationSubmit={(ids) => void submitDisambiguation(ids)}
              onDisambiguationGenrePick={(genre) => void submitDisambiguationGenre(genre)}
              pickerDisabled={chatLoading}
              addSeedDisabled={chatLoading}
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
              defaultOpen={hasThread}
              availableGenres={genres}
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
            {!hasThread && (
              <GenreChipsRow
                genres={genres}
                selected={selectedGenres}
                loading={genresLoading}
                disabled={chatLoading}
                onToggle={toggleGenre}
              />
            )}
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
                <button
                  type="button"
                  className="ghost"
                  onClick={() => void startOver()}
                  disabled={chatLoading}
                >
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
            availableGenres={genres}
            {...tasteHandlers}
          />
        )}
      </section>
    </div>
  )
}
