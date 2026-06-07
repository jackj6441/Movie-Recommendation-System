import type { ChatTurnView } from "./lib/chatTurnView"

export type MoviePosters = {
  poster_url?: string
  poster_thumb_url?: string
}

export type RecommendationItem = MoviePosters & {
  movie_id: number
  title: string
  score: number
}

export type RecommendationResponse = {
  items: RecommendationItem[]
  seed_movies: (MoviePosters & { movie_id: number; title: string })[]
  anchor_source: string
  model_version: string
}

export type ChatSeedRef = MoviePosters & {
  movie_id: number
  title: string
}

export type RagChatContext = {
  seeds: ChatSeedRef[]
  genres: string[]
  year_min: number | null
  year_max: number | null
  recency_opt_out?: boolean
}

export type DisambiguationCandidate = MoviePosters & {
  movie_id: number
  title: string
  year?: number
  genres?: string[]
  match_score?: number
}

export type RagChatDebug = {
  resolve_outcome: string
  seed_source?: string
  normalized_genres?: string[]
  candidate_count?: number
  ranking_mode?: string
}

export type RagChatFinal = {
  session_id: string
  turn_id: string
  needs_clarification: boolean
  needs_disambiguation: boolean
  clarification_reason?: string
  disambiguation_candidates?: DisambiguationCandidate[]
  disambiguation_genre_options?: string[]
  pending_genres?: string[]
  warnings?: { code: string; movie_id?: number }[]
  debug?: RagChatDebug
  context: RagChatContext
  recommendations: RecommendationResponse | null
  assistant_message: string
  explanation_source: "rag" | "deterministic_fallback"
  chat_fallback_reason?: string
  model_version?: string
  rank_error?: string
}

export type RagChatStreamResult = {
  tokens: string
  view: ChatTurnView
  assistantMessage: string
}

export type { ChatTurnView } from "./lib/chatTurnView"

export type ChatTurn = {
  id: string
  role: "user" | "assistant"
  content: string
  streaming?: boolean
  view?: ChatTurnView
}

export type MovieSuggestion = MoviePosters & {
  movie_id: number
  title: string
}

export type SystemEvidence = {
  system_name: string
  deployment: {
    platform: string
    runtime: string
    ui_url: string
    api_url: string
  }
  serving: {
    status: string
    content_ok: boolean
    catalog_ok: boolean
    model_version: string
  }
  model_truth: {
    product_ranking_path: string
    roadmap?: string
  }
  evaluation: {
    recall_at_k: number
    ndcg_at_k: number
    recommendation_coverage: number
    topk_diversity: number
    popularity_baseline_recall_at_k: number
  }
  benchmark: {
    recommendations_p95_ms: number
    rag_chat_p95_ms?: number
    rag_explanations_p95_ms?: number
  }
  rag: {
    public_provider: string
    secret_policy: string
  }
}
