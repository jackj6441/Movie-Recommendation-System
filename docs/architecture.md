# Architecture

## High-Level Components

1. **Training (offline)**
   - MovieLens ratings + served catalog (`catalog_movies.csv`).
   - Content embeddings: SentenceTransformer on title + genres → `content_embeddings.npz`.
   - Serving stats: popularity counts → `serving_stats.json`.
   - Phase 1 retrieval artifacts: `item_factors_svd.npz`, `item_neighbors.json`.
   - Optional: TMDB poster lookup (`poster_urls.json`).

2. **Serving (FastAPI)**
   - Seed-set product flow only (no `user_id`, no ONNX/NCF, no Redis).
   - Phase 1 ranking: four retrievers → union (cap 400) → weighted fusion → Top-24.
   - Conversational RAG (`POST /rag/chat`, SSE + session store; ranking unchanged).

3. **Frontend (React)**
   - Chat-first recommender (`POST /rag/chat` SSE, genre chips, embedded cards) + System Evidence tab.

4. **Evaluation & benchmarks**
   - `evaluation/eval_fusion.py`: Recall/NDCG @10 and @24.
   - `evaluation/tune_fusion_weights.py`: grid search → `fusion_weights.json`.
   - `benchmarks/benchmark_api.py`: HTTP latency harness + optional portfolio evidence sync.

## Offline Data Flow

```text
movies.csv + ratings.csv (32M)
  -> build_content_embeddings.py  -> content_embeddings.npz, content_index.json, catalog_movies.csv
  -> build_serving_stats.py       -> serving_stats.json
  -> build_svd_factors.py        -> item_factors_svd.npz
  -> build_item_neighbors.py     -> item_neighbors.json
  -> tune_fusion_weights.py      -> fusion_weights.json (optional)
```

All served movie ids share the same catalog boundary (`content_index.json` row order).

## Online Ranking (Phase 1 fusion)

```text
POST /recommendations { seeds[1..5] }
  -> validate seeds against catalog + content index
  -> retrievers (each Top-200, exclude seeds):
       content  : cosine vs mean seed embedding (full catalog scan)
       svd      : dot product vs mean seed factor vector
       item_cf  : aggregate neighbor scores from item_neighbors.json
       pop      : top popular movies from serving_stats
  -> merge union, dedupe, cap 400 (by best raw channel score)
  -> optional genre/year filters on merged ids
  -> per-channel min-max on each Top-200 list; missing channel = 0
  -> final = weighted sum using fusion_weights.json
  -> return Top-24 (API field score = fusion_score)
```

## Online product flow (conversational RAG)

```text
POST /rag/chat { message, genres[], session_id? }
  -> SessionStore (TTL) + resolve_context (search, genre bootstrap, year hints)
  -> seed_ranker.rank (same as POST /recommendations)
  -> SSE: token deltas + final { assistant_message, recommendations, context }
```

`POST /explanations` remains for debug signal inspection only (not used by the UI).

## Key Artifacts (`services/reco-api/models/`)

| File | Purpose |
|------|---------|
| `content_embeddings.npz` | Content vectors |
| `content_index.json` | movieId → row |
| `catalog_movies.csv` | Search / seeds / titles |
| `serving_stats.json` | Popularity for pop retriever + startup counts |
| `item_factors_svd.npz` | SVD item factors (optional until built) |
| `item_neighbors.json` | Item–item CF neighbors (optional) |
| `fusion_weights.json` | Phase 1 channel weights |
| `poster_urls.json` | UI thumbnails (optional) |

## Observability

- `GET /healthz`: `content_ok`, `catalog_ok`, `ranking_mode`, `fusion_ok`, `svd_ok`, `item_cf_ok`, poster fields.
- `GET /metrics`: Prometheus text (requests, latency, RAG outcomes).
- `GET /system/evidence`: portfolio snapshot; benchmark block updated via `benchmark_api.py --sync-evidence`.

## Configuration (env)

| Variable | Role |
|----------|------|
| `CANDIDATE_POOL` | Legacy pool hint (filters widen candidate base) |
| `CONTENT_EMBEDDINGS_PATH` | NPZ path |
| `ITEM_FACTORS_SVD_PATH` | SVD artifact |
| `ITEM_NEIGHBORS_PATH` | Item-CF artifact |
| `FUSION_WEIGHTS_PATH` | Weight JSON |
| `RAG_PROVIDER` | `mock` / `external` / test modes |

## Phase 2 (LightGBM Lambdarank)

- Offline: `training/train_lambdarank.py` on four normalized channel features per candidate.
- Labels: graded relevance (`rating >= 4` → 2, `3` → 1, else 0) for held-out next-item queries.
- Artifacts: `ltr_model.txt`, `ltr_meta.json`.
- Serving: set `RANKING_MODE=ltr` (falls back to fusion if model missing).
- API field `score` / `final` still exposed as `fusion_score` for UI/RAG compatibility.
