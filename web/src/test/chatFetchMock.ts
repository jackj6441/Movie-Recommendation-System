import { vi } from "vitest"
import type { RecommendationItem } from "../types"

export type ChatMockConfig = {
  chatOk?: boolean
  needsClarification?: boolean
  clarificationReason?: string
  emptyRecommendations?: boolean
  needsDisambiguation?: boolean
  disambiguationCandidates?: {
    movie_id: number
    title: string
    year?: number
    genres?: string[]
  }[]
  assistantMessage?: string
  items?: RecommendationItem[]
  seedMovies?: { movie_id: number; title: string }[]
  includeEvidence?: boolean
  /** When true, SSE body has only a final event (no token stream). */
  finalOnly?: boolean
}

const defaultItems: RecommendationItem[] = [
  { movie_id: 239, title: "Some Movie (1999)", score: 0.9 },
]

const defaultSeeds = [{ movie_id: 1, title: "Toy Story (1995)" }]

export function buildSseBody(config: ChatMockConfig): string {
  const assistantMessage =
    config.assistantMessage ??
    "Based on your Seed Set, here are movies that match your taste."
  let body = ""
  if (!config.finalOnly) {
    const tokens = assistantMessage.split(/(?=\s)/)
    for (const delta of tokens) {
      body += `event: token\ndata: ${JSON.stringify({ delta })}\n\n`
    }
  }
  const final = {
    session_id: "sess-test-1",
    turn_id: "turn-test-1",
    needs_clarification:
      config.needsClarification ?? config.emptyRecommendations ?? false,
    needs_disambiguation: config.needsDisambiguation ?? false,
    clarification_reason: config.clarificationReason,
    model_version: "test-model",
    disambiguation_candidates: config.needsDisambiguation
      ? (config.disambiguationCandidates ?? [
          { movie_id: 50, title: "Candidate Movie (2000)", genres: ["Drama"] },
        ])
      : undefined,
    context: {
      seeds: defaultSeeds,
      genres: ["Comedy"],
      year_min: null,
      year_max: null,
    },
    recommendations:
      config.emptyRecommendations
        ? {
            items: [],
            seed_movies: config.seedMovies ?? defaultSeeds,
            anchor_source: "seed",
            model_version: "test-model",
            ranking_mode: "multi_retriever_fusion",
          }
        : config.needsClarification && !config.emptyRecommendations
          ? null
          : {
              items: config.items ?? defaultItems,
              seed_movies: config.seedMovies ?? defaultSeeds,
              anchor_source: "seed",
              model_version: "test-model",
              ranking_mode: "multi_retriever_fusion",
            },
    assistant_message: assistantMessage,
    explanation_source: "rag",
  }
  body += `event: final\ndata: ${JSON.stringify(final)}\n\n`
  return body
}

export function sseResponse(body: string, ok = true): Promise<Response> {
  return Promise.resolve({
    ok,
    status: ok ? 200 : 500,
    headers: {
      get: (name: string) =>
        name.toLowerCase() === "content-type" ? "text/event-stream" : null,
    },
    text: () => Promise.resolve(body),
    json: () => Promise.reject(new Error("SSE response")),
  } as Response)
}

export function jsonResponse(payload: unknown): Promise<Response> {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(payload),
  } as Response)
}

export function createFetchMock(config: ChatMockConfig = {}) {
  return vi.fn((input: RequestInfo | URL) => {
    const url = input.toString()

    if (url.endsWith("/genres")) {
      return jsonResponse([{ name: "Comedy" }, { name: "Drama" }])
    }

    if (url.endsWith("/rag/chat")) {
      if (config.chatOk === false) {
        return Promise.reject(new Error("Chat unavailable"))
      }
      return sseResponse(buildSseBody(config))
    }

    if (url.endsWith("/system/evidence")) {
      return jsonResponse({
        system_name: "movie-recommendation-system",
        deployment: {
          platform: "AWS EC2",
          runtime: "Docker Compose",
          ui_url: "http://localhost:3000",
          api_url: "http://localhost:8000",
        },
        serving: {
          status: "ok",
          content_ok: true,
          catalog_ok: true,
          model_version: "dev",
        },
        model_truth: {
          product_ranking_path: "Seed Set recommendations via multi-retriever fusion",
        },
        evaluation: {
          recall_at_k: 0.05,
          ndcg_at_k: 0.0258,
          recommendation_coverage: 0.0287,
          topk_diversity: 0.5997,
          popularity_baseline_recall_at_k: 0.02,
        },
        benchmark: {
          recommendations_p95_ms: 65.459,
          rag_chat_p95_ms: 5.088,
        },
        rag: {
          public_provider: "mock",
          secret_policy: "real provider keys stay backend-only",
        },
      })
    }

    throw new Error(`Unhandled request: ${url}`)
  })
}
