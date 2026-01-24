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
