# Architecture

## High-Level Components

1. Training
   - Data prep: MovieLens ratings + movies metadata.
   - NCF model: user/item embeddings + MLP for explicit ratings.
   - Export: ONNX model + metadata.json.
   - Content embeddings: transformer embeddings stored in NPZ.

2. Serving (FastAPI)
   - ONNX Runtime inference for NCF scoring.
   - Content embeddings for similarity scoring.
   - Redis cache for recommendations/explanations.

3. Frontend (React + D3)
   - Wizard flow: genres -> seeds -> recommendations.
   - Explain panel: stacked bars with contributions.

## Data Flow

- Offline
  1) Load ratings.csv, movies.csv.
  2) Train NCF model and export to ONNX.
  3) Build content embeddings from title + genres.
  4) Persist artifacts to `services/reco-api/models/`.

- Online (seed-based)
  1) User selects seeds.
  2) API computes mean seed embedding.
  3) Score candidate pool with cosine similarity.
  4) Return top-k + explain payload.

## Key Artifacts

- `services/reco-api/models/ncf.onnx`
- `services/reco-api/models/metadata.json`
- `services/reco-api/models/content_embeddings.npz`
- `services/reco-api/models/content_index.json`
- `services/reco-api/models/poster_urls.json` (offline TMDB poster URLs; built locally via `training/build_poster_lookup.py`)
- `services/reco-api/models/poster_meta.json` (poster coverage stats for `/healthz`)

## Caching

- /recommend uses Redis cache (versioned key by model_version).
- /explain uses short TTL cache for UI explainability.

## Configuration

- `CANDIDATE_POOL`: size of candidate pool.
- `CACHE_TTL_SECONDS`: recommendation cache TTL.
- `EXPLAIN_TTL_SECONDS`: explain cache TTL.
- `ALPHA`: hybrid weight for NCF vs content.
