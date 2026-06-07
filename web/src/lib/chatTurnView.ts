import type {
  DisambiguationCandidate,
  RagChatContext,
  RagChatDebug,
  RagChatFinal,
  RecommendationResponse,
} from "../types"

export type ChatTurnOutcome = "ready" | "clarify" | "disambiguate" | "error"

export type ChatDisambiguationView = {
  candidates: DisambiguationCandidate[]
  genreOptions?: string[]
}

export type ChatTurnView = {
  sessionId: string
  turnId: string
  outcome: ChatTurnOutcome
  assistantMessage: string
  context: RagChatContext
  recommendations: RecommendationResponse | null
  disambiguation: ChatDisambiguationView | null
  debug: RagChatDebug | null
  clarificationReason?: string
  explanationSource: "rag" | "deterministic_fallback"
  chatFallbackReason?: string
  rankError?: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function readString(row: Record<string, unknown>, key: string): string {
  const value = row[key]
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`Chat final payload missing ${key}`)
  }
  return value
}

function readBool(row: Record<string, unknown>, key: string): boolean {
  const value = row[key]
  if (typeof value !== "boolean") {
    throw new Error(`Chat final payload missing ${key}`)
  }
  return value
}

function readContext(row: Record<string, unknown>): RagChatContext {
  const context = row.context
  if (!isRecord(context)) {
    throw new Error("Chat final payload missing context")
  }
  const seeds = Array.isArray(context.seeds) ? context.seeds : []
  const genres = Array.isArray(context.genres)
    ? context.genres.filter((genre): genre is string => typeof genre === "string")
    : []
  return {
    seeds: seeds
      .filter(isRecord)
      .map((seed) => ({
        movie_id: Number(seed.movie_id),
        title: String(seed.title ?? ""),
      }))
      .filter((seed) => Number.isFinite(seed.movie_id) && seed.title),
    genres,
    year_min: typeof context.year_min === "number" ? context.year_min : null,
    year_max: typeof context.year_max === "number" ? context.year_max : null,
    recency_opt_out: context.recency_opt_out === true,
  }
}

/** Validate and coerce the backend SSE final payload at the wire boundary. */
export function parseRagChatFinal(data: unknown): RagChatFinal {
  if (!isRecord(data)) {
    throw new Error("Chat final payload must be an object")
  }

  const final: RagChatFinal = {
    session_id: readString(data, "session_id"),
    turn_id: readString(data, "turn_id"),
    needs_clarification: readBool(data, "needs_clarification"),
    needs_disambiguation: readBool(data, "needs_disambiguation"),
    context: readContext(data),
    recommendations: null,
    assistant_message:
      typeof data.assistant_message === "string" ? data.assistant_message : "",
    explanation_source:
      data.explanation_source === "deterministic_fallback"
        ? "deterministic_fallback"
        : "rag",
  }

  if (typeof data.clarification_reason === "string") {
    final.clarification_reason = data.clarification_reason
  }
  if (Array.isArray(data.disambiguation_candidates)) {
    final.disambiguation_candidates = data.disambiguation_candidates as DisambiguationCandidate[]
  }
  if (Array.isArray(data.disambiguation_genre_options)) {
    final.disambiguation_genre_options = data.disambiguation_genre_options.filter(
      (genre): genre is string => typeof genre === "string",
    )
  }
  if (Array.isArray(data.pending_genres)) {
    final.pending_genres = data.pending_genres.filter(
      (genre): genre is string => typeof genre === "string",
    )
  }
  if (Array.isArray(data.warnings)) {
    final.warnings = data.warnings as RagChatFinal["warnings"]
  }
  if (isRecord(data.debug)) {
    final.debug = data.debug as RagChatDebug
  }
  if (isRecord(data.recommendations) || data.recommendations === null) {
    final.recommendations = data.recommendations as RecommendationResponse | null
  }
  if (typeof data.chat_fallback_reason === "string") {
    final.chat_fallback_reason = data.chat_fallback_reason
  }
  if (typeof data.model_version === "string") {
    final.model_version = data.model_version
  }
  if (typeof data.rank_error === "string") {
    final.rank_error = data.rank_error
  }

  return final
}

function resolveOutcome(raw: RagChatFinal): ChatTurnOutcome {
  if (raw.needs_disambiguation) return "disambiguate"
  if (raw.rank_error) return "error"
  if (raw.needs_clarification) return "clarify"
  return "ready"
}

/** Map a validated backend final payload into UI turn state. */
export function toChatTurnView(
  raw: RagChatFinal,
  options?: { streamedText?: string },
): ChatTurnView {
  const streamedText = options?.streamedText?.trim() ?? ""
  const assistantMessage = raw.assistant_message.trim() || streamedText

  const disambiguation =
    raw.needs_disambiguation && raw.disambiguation_candidates?.length
      ? {
          candidates: raw.disambiguation_candidates,
          genreOptions: raw.disambiguation_genre_options,
        }
      : null

  return {
    sessionId: raw.session_id,
    turnId: raw.turn_id,
    outcome: resolveOutcome(raw),
    assistantMessage,
    context: raw.context,
    recommendations: raw.recommendations,
    disambiguation,
    debug: raw.debug ?? null,
    clarificationReason: raw.clarification_reason,
    explanationSource: raw.explanation_source,
    chatFallbackReason: raw.chat_fallback_reason,
    rankError: raw.rank_error,
  }
}

type StoredChatTurn = {
  id: string
  role: "user" | "assistant"
  content: string
  streaming?: boolean
  view?: ChatTurnView
  final?: RagChatFinal
}

/** Upgrade persisted turns that still store the raw backend final payload. */
export function normalizeChatTurn<T extends StoredChatTurn>(turn: T): T {
  if (turn.view || turn.role !== "assistant" || !turn.final) {
    return turn
  }
  return {
    ...turn,
    view: toChatTurnView(turn.final, { streamedText: turn.content }),
  }
}
