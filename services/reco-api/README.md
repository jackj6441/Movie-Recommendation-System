# Reco API

FastAPI seed-based movie recommendation service with content embeddings and RAG explanations.

## Environment variables

- `MOVIES_CSV_PATH`: Served catalog CSV (`catalog_movies.csv` in Docker).
- `SERVING_STATS_PATH`: Precomputed `serving_stats.json` (popularity, num_users, num_items).
- `RATINGS_CSV_PATH`: Fallback ratings CSV when serving stats are missing (local dev/CI).
- `CONTENT_EMBEDDINGS_PATH` / `CONTENT_INDEX_PATH`: Content embedding NPZ and index JSON.
- `POSTER_URLS_PATH` / `POSTER_META_PATH`: Offline TMDB poster lookup artifacts.
- `CANDIDATE_POOL`: Candidate pool size for content ranking (default `500`).
- `MODEL_VERSION`: Response `model_version` label.
- `CORS_ALLOW_ORIGINS`: Comma-separated browser origins.
- `RAG_PROVIDER`, `RAG_PROVIDER_API_KEY`, `RAG_PROVIDER_MODEL`: RAG explanation provider (default `mock`).
- `RAG_EXTERNAL_RESPONSE_JSON`: Test-only override for external provider responses.
- External provider calls use an 8-second timeout before deterministic fallback.

## Product endpoints

- `POST /recommendations` — seed-based ranking (content embeddings).
- `POST /explanations` — deterministic score breakdown for RAG evidence.
- `POST /rag/explanations` — structured natural-language explanations.
- `GET /healthz`, `GET /metrics`, `GET /system/evidence`
