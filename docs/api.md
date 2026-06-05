# API Reference

Base URL: `http://localhost:8000`

## Health

### GET /healthz

Returns service readiness health and config. Use this endpoint to decide whether the API process can serve traffic and whether required runtime dependencies are available.

Response:
```json
{
  "status": "ok",
  "content_ok": true,
  "catalog_ok": true,
  "num_users": 610,
  "num_items": 9724,
  "model_version": "dev",
  "candidate_pool": 500,
  "ranking_mode": "multi_retriever_fusion",
  "fusion_ok": true,
  "fusion_weights_ok": true,
  "svd_ok": true,
  "item_cf_ok": true,
  "poster_ok": true,
  "poster_count": 21000,
  "poster_coverage": 0.9
}
```

`poster_ok`, `poster_count`, and `poster_coverage` come from the offline `poster_urls.json` / `poster_meta.json` artifacts (no TMDB calls at runtime).

## Observability

### GET /metrics

Returns Prometheus-style `text/plain` metrics for runtime observability. Use this endpoint to inspect request volume, latency, cache behavior, and RAG explanation outcomes over time.

`/healthz` answers "is the service ready right now?" while `/metrics` answers "what has the service been doing?"

Example metrics:

```text
movie_reco_requests_total{endpoint="/healthz",status="200"} 1
movie_reco_request_latency_ms_count{endpoint="/healthz",status="200"} 1
movie_reco_request_latency_ms_sum{endpoint="/healthz",status="200"} 2.341
movie_reco_cache_events_total{cache="redis",event="hit"} 1
movie_reco_rag_chat_turns_total{outcome="success"} 1
movie_reco_rag_chat_reasons_total{reason="provider_timeout"} 1
movie_reco_rag_provider_mode{provider="mock"} 1
```

## Movie Search

### GET /movies/search?q=...

Case-insensitive substring search by title. Returns up to 20 matches.

Response:
```json
[
  {
    "movie_id": 1,
    "title": "Toy Story (1995)",
    "poster_url": "https://image.tmdb.org/t/p/w500/...",
    "poster_thumb_url": "https://image.tmdb.org/t/p/w185/..."
  }
]
```

`poster_url` and `poster_thumb_url` are optional. They are omitted when no offline lookup exists for that movie.

## Genres

### GET /genres

Returns all distinct genres.

Response:
```json
[{"name": "Action"}, {"name": "Drama"}]
```

### GET /genres/{genre}/seeds?limit=20

Returns popular seed movies for a genre.

Response:
```json
{
  "seeds": [
    {
      "movie_id": 356,
      "title": "Forrest Gump (1994)",
      "poster_url": "https://image.tmdb.org/t/p/w500/...",
      "poster_thumb_url": "https://image.tmdb.org/t/p/w185/..."
    }
  ]
}
```

## Seed Recommendations (Product)

### POST /recommendations

Body:
```json
{"seeds": [356, 260, 318, 1198, 1210], "shuffle": false, "genres": ["Comedy", "Drama"], "year_min": 1990, "year_max": 1999}
```

Fields:

- `seeds` (required): 1 to 5 movie IDs to anchor recommendations.
- `shuffle` (optional, default `false`): randomize the candidate pool for variety.
- `genres` (optional): list of genre names. A movie matches if it has **any** of the listed genres (OR semantics). Omit or send `null`/`[]` for no genre filter.
- `year_min` / `year_max` (optional): inclusive release-year bounds parsed from the movie title. Omit either side for an open range.

When any filter is active the candidate pool widens to the full catalog so niche filters still surface matches; ranking by seed similarity is unchanged. The endpoint returns up to 24 ranked items (the UI shows the first 3 as featured picks and the rest as a poster grid). If no candidate satisfies the filters, `items` is an empty array.

Response:
```json
{
  "items": [
    {
      "movie_id": 186,
      "title": "Nine Months (1995)",
      "score": 0.74,
      "poster_url": "https://image.tmdb.org/t/p/w500/...",
      "poster_thumb_url": "https://image.tmdb.org/t/p/w185/..."
    }
  ],
  "seed_movies": [
    {
      "movie_id": 356,
      "title": "Forrest Gump (1994)",
      "poster_url": "https://image.tmdb.org/t/p/w500/...",
      "poster_thumb_url": "https://image.tmdb.org/t/p/w185/..."
    }
  ],
  "anchor_source": "seed",
  "model_version": "dev"
}
```

### POST /explanations

Body (same `SeedsRequest` as `/recommendations`, including the optional `genres`, `year_min`, and `year_max` filters):
```json
{"seeds": [356, 260, 318, 1198, 1210], "shuffle": false}
```

Response:
```json
{
  "user_id": null,
  "model_version": "dev",
  "anchor_movie": {"movie_id": 356, "title": "Forrest Gump (1994)"},
  "seed_movies": [{"movie_id": 356, "title": "Forrest Gump (1994)"}],
  "topk": [
    {"movie_id": 356, "title": "Forrest Gump (1994)", "content": 0.64, "final": 0.64}
  ],
  "similar_movies": [{"movie_id": 296, "title": "Pulp Fiction (1994)", "similarity": 0.64}],
  "content_available": true,
  "anchor_source": "seed"
}
```

## Conversational RAG (Product)

### POST /rag/chat

Server-sent events (`text/event-stream`) for a single chat turn. The backend resolves **Seed Set** and filters from the user message and genre chips, runs the same ranker as `POST /recommendations`, streams assistant prose, then emits a **final** event with optional **Recommendation List**. Ranking is never changed by the language model.

Request:
```json
{
  "session_id": null,
  "message": "more 90s sci-fi",
  "genres": ["Sci-Fi"],
  "shuffle": false
}
```

- `session_id`: omit or `null` to start a session; pass the id from a prior `final` event to continue.
- `genres`: up to 3 genre chip selections from the UI.
- Clarification: when there are no genres, no resolvable movie titles in `message`, and no seeds in the session, the `final` event sets `needs_clarification: true` and omits `recommendations`.

SSE events:

- `token`: `{"delta": "..."}` — streamed assistant text.
- `final`: full turn payload (see below).

Example `final` (recommendations ready):
```json
{
  "session_id": "uuid",
  "turn_id": "uuid",
  "needs_clarification": false,
  "context": {
    "seeds": [{"movie_id": 1, "title": "Toy Story (1995)"}],
    "genres": ["Comedy"],
    "year_min": null,
    "year_max": null
  },
  "recommendations": {
    "items": [{"movie_id": 186, "title": "...", "score": 0.74}],
    "seed_movies": [{"movie_id": 1, "title": "Toy Story (1995)"}],
    "anchor_source": "seed",
    "model_version": "dev",
    "ranking_mode": "multi_retriever_fusion"
  },
  "assistant_message": "Based on your Seed Set ...",
  "explanation_source": "rag",
  "rag_chat_version": "conversational-v1",
  "prompt_version": "rag-chat-v1"
}
```

- `explanation_source`: `rag` or `deterministic_fallback` when the provider fails but ranking succeeded.
- `chat_fallback_reason`: optional (`provider_timeout`, `provider_error`, …).
- `503` / rank errors: `final` may include `rank_error: "content_unavailable"` and null `recommendations`.

Configuration:

- `RAG_PROVIDER`: `mock` (default), `external`, or test modes (`mock_timeout`, `mock_provider_error`, …).
- `RAG_PROVIDER_API_KEY`, `RAG_PROVIDER_MODEL`: backend-only for `external`.
- `RAG_SESSION_TTL_SECONDS`: in-memory session TTL (default `3600`).
- `RAG_PROMPT_VERSION`: overrides default `rag-chat-v1`.

The legacy `POST /rag/explanations` endpoint has been removed.

## Debug Endpoints

### GET /debug/similar
Content-based similarity for a movie (debug only).
