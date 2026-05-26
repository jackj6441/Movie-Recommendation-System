# Reco API

Placeholder for FastAPI + ONNX Runtime + Redis service.

## Environment variables

- `REDIS_URL`: Redis connection string.
- `ONNX_MODEL_PATH`: Path to `ncf.onnx` inside the container.
- `METADATA_PATH`: Path to `metadata.json` inside the container.
- `MOVIES_CSV_PATH`: Path to MovieLens `movies.csv`.
- `RATINGS_CSV_PATH`: Path to MovieLens `ratings.csv`.
- `CANDIDATE_POOL`: Number of candidate movies scored by ONNX.
- `CACHE_TTL_SECONDS`: TTL for `/recommend` cache.
- `EXPLAIN_TTL_SECONDS`: TTL for `/explain` cache.
- `ALPHA`: Weight for NCF vs content fusion.
- `RAG_PROVIDER`: RAG explanation provider mode. Use `mock` for local development or `external` for backend-only external provider integration.
- `RAG_PROVIDER_API_KEY`: Backend-only API key for the external RAG provider. Use a secret manager or local environment variable; do not commit real values.
- `RAG_PROVIDER_MODEL`: External provider model name used in RAG cache keys and metadata logs.
- `RAG_EXTERNAL_RESPONSE_JSON`: Test-only backend override for provider responses; do not use for production traffic.
- External RAG provider calls follow an 8-second timeout policy before falling back to deterministic explanations.
