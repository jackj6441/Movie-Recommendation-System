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
  "ranking_mode": "content_seed",
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
movie_reco_rag_explanations_total{source="rag"} 1
movie_reco_rag_fallback_reasons_total{reason="invalid_json"} 1
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

## RAG Explanations (Product)

### POST /rag/explanations

Generates a structured natural-language explanation for an existing Recommendation List. The endpoint runs deterministic `/explanations` internally, builds RAG evidence from that result, and explains the top 3 of `topk` in order. RAG never changes ranking; it only describes recommendations that were already selected. v1 is English-only, non-streaming, top-3 item explanations, and uses structured project data only.

Body (same `SeedsRequest` as `/explanations`):
```json
{"seeds": [356, 260, 318, 1198, 1210], "shuffle": false}
```

Validation matches `/explanations`:

- `400 {"detail": "seeds must be 1 to 5 items"}` when seeds is empty or has more than 5 items.
- `400 {"detail": "no valid seeds"}` when no seed maps to a known movie.
- `503 {"content_unavailable": true}` when content embeddings are unavailable.

Success response (`explanation_source: "rag"`):
```json
{
  "summary": "Based on your Seed Set (Forrest Gump (1994), ...), these Recommendations emphasize movies with similar content signals and strong fusion scores.",
  "items": [
    {
      "movie_id": 356,
      "reason": "Forrest Gump (1994) is recommended because it aligns with your Seed Set through content similarity and its fusion score.",
      "evidence": ["seed_set", "content_signal", "fusion_score"]
    }
  ],
  "model_version": "dev",
  "rag_evidence_version": "structured-v1",
  "evidence_hash": "sha256:...",
  "prompt_version": "rag-chatgpt-v1",
  "request_id": "5f1c...",
  "explanation_source": "rag"
}
```

Field and enum reference:

- `explanation_source`: one of `rag` (freshly generated), `rag_cache` (served from cache), `deterministic_fallback` (provider unavailable or output rejected).
- `items[].evidence`: subset of `seed_set`, `content_signal`, `fusion_score`.
- `items` preserve Recommendation List order and cover the top 3 of `topk` (fewer when fewer than 3 recommendations exist).
- `rag_evidence_version`: evidence schema version, currently `structured-v1`.
- `prompt_version`: prompt version and cache-key input, default `rag-chatgpt-v1` (override with `RAG_PROMPT_VERSION`).
- `evidence_hash`: `sha256:` digest of the canonicalized deterministic explanation used for this request.
- `request_id`: unique id per request, for log correlation.
- `fallback_reason`: present only on fallback responses. Emitted values: `provider_timeout`, `provider_error`, `invalid_json`, `schema_validation_failed`, `disabled`, `unknown`.

Cache behavior: when `RAG_CACHE_ENABLED=true`, an equivalent request returns the same payload with `explanation_source: "rag_cache"`. The cache key combines model version, evidence hash, prompt version, provider, and provider model, so any change to those misses the cache.

Fallback response (`explanation_source: "deterministic_fallback"`), e.g. on provider timeout or schema validation failure:
```json
{
  "summary": "These Recommendations are based on your Seed Set and existing scoring signals.",
  "items": [
    {
      "movie_id": 356,
      "reason": "This Recommendation is based on your Seed Set and existing scoring signals.",
      "evidence": ["seed_set", "content_signal", "fusion_score"]
    }
  ],
  "model_version": "dev",
  "rag_evidence_version": "structured-v1",
  "evidence_hash": "sha256:...",
  "prompt_version": "rag-chatgpt-v1",
  "request_id": "5f1c...",
  "explanation_source": "deterministic_fallback",
  "fallback_reason": "provider_timeout"
}
```

Empty Recommendation List behavior: when there are no recommendations, `items` is an empty array and `summary` still returns. Under the default `mock` provider this comes back as `explanation_source: "rag"` with empty `items`.

Configuration (backend environment only):

- `RAG_PROVIDER`: `mock` (default) or `external` for the real OpenAI provider. Additional `mock_*` failure modes exist for tests.
- `RAG_PROVIDER_API_KEY`: required only when `RAG_PROVIDER=external`. Backend-only; never expose in frontend code or commit it.
- `RAG_PROVIDER_MODEL`: provider model, default `mock` (for example `gpt-4o-mini`).
- `RAG_CACHE_ENABLED`: `true`/`false`, default `false`.
- `RAG_CACHE_TTL_SECONDS`: cache TTL, default `3600`.
- External provider calls use an 8-second timeout; the endpoint targets 10 seconds or less overall.

## Debug Endpoints

### GET /debug/similar
Content-based similarity for a movie (debug only).
