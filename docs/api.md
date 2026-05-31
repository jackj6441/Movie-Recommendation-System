# API Reference

Base URL: `http://localhost:8000`

## Health

### GET /healthz

Returns service readiness health and config. Use this endpoint to decide whether the API process can serve traffic and whether required runtime dependencies are available.

Response:
```json
{
  "status": "ok",
  "redis_ok": true,
  "onnx_ok": true,
  "metadata_ok": true,
  "num_users": 610,
  "num_items": 9724,
  "tfidf_ok": false,
  "model_version": "dev",
  "candidate_pool": 500,
  "cache_ttl_seconds": 300,
  "explain_ttl_seconds": 60,
  "alpha": 0.7
}
```

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
[{"movie_id": 1, "title": "Toy Story (1995)"}]
```

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
{"seeds": [{"movie_id": 356, "title": "Forrest Gump (1994)"}]}
```

## Seed Recommendations (Product)

### POST /recommendations

Body:
```json
{"seeds": [356, 260, 318, 1198, 1210], "shuffle": false}
```

Response:
```json
{
  "items": [{"movie_id": 186, "title": "Nine Months (1995)", "score": 0.74}],
  "seed_movies": [{"movie_id": 356, "title": "Forrest Gump (1994)"}],
  "anchor_source": "seed",
  "model_version": "dev"
}
```

### POST /explanations

Body:
```json
{"seeds": [356, 260, 318, 1198, 1210], "shuffle": false}
```

Response:
```json
{
  "user_id": null,
  "model_version": "dev",
  "alpha": 0.7,
  "anchor_movie": {"movie_id": 356, "title": "Forrest Gump (1994)"},
  "seed_movies": [{"movie_id": 356, "title": "Forrest Gump (1994)"}],
  "topk": [
    {"movie_id": 356, "title": "Forrest Gump (1994)", "ncf": 0.0, "content": 0.64, "final": 0.64}
  ],
  "similar_movies": [{"movie_id": 296, "title": "Pulp Fiction (1994)", "similarity": 0.64}],
  "content_available": true,
  "anchor_source": "seed"
}
```

## Debug Endpoints

### GET /recommend
Legacy debug endpoint (user_id + k). Not used by UI.

### GET /explain
Legacy debug endpoint (user_id + k). Not used by UI.

### GET /score
NCF model score for a single user/movie index.

### GET /debug/similar
Content-based similarity for a movie.
