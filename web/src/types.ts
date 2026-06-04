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
  seed_movies: { movie_id: number; title: string }[]
  anchor_source: string
  model_version: string
}

export type ExplainItem = {
  movie_id: number
  title: string
  content: number
  final: number
}

export type SimilarMovie = {
  movie_id: number
  title: string
  similarity: number
}

export type ExplainResponse = {
  user_id: number | null
  model_version: string
  anchor_movie: { movie_id: number; title: string } | null
  topk: ExplainItem[]
  similar_movies: SimilarMovie[]
  content_available: boolean
  seed_movies?: { movie_id: number; title: string }[]
  anchor_source?: string
}

export type RagExplanationItem = {
  movie_id: number
  reason: string
  evidence: string[]
}

export type RagExplanationResponse = {
  summary: string
  items: RagExplanationItem[]
  explanation_source: "rag" | "rag_cache" | "deterministic_fallback"
  fallback_reason?: string | null
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
    rag_explanations_p95_ms: number
  }
  rag: {
    public_provider: string
    secret_policy: string
  }
}
