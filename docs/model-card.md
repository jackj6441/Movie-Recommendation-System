# Model Card: Movie Recommendation System

## Dataset

- Product catalog and content embeddings: MovieLens **32M** (`ml-32m`), movies with at least **20** ratings (~23k titles in `catalog_movies.csv`).
- Required serving files today: `catalog_movies.csv`, `content_embeddings.npz`, `content_index.json`, `serving_stats.json`.
- Phase 1 fusion (offline, M2 serving): `item_factors_svd.npz`, `item_neighbors.json` from `training/build_svd_factors.py` and `training/build_item_neighbors.py`.
- Full `ml-32m/ratings.csv` is used offline only (not loaded at API startup).
- Dataset versioning is currently file-based. A future Model Registry phase should record a formal dataset version with each model artifact.

## Split Strategy

- The NCF rating model uses per-user chronological splitting.
- Users with at least three ratings contribute earlier interactions to training, the second-to-last interaction to validation, and the last interaction to test.
- The evaluation harness uses a per-user held-out interaction for rating RMSE and retrieval-style ranking checks.

## Metrics

The evaluation harness is expected to report:

- Recall@10 / Recall@24 and NDCG@10 / NDCG@24 for Phase 1 fusion (`evaluation/eval_fusion.py`).
- Legacy Recall@K / NDCG@K for content-only baseline (`evaluation/eval_retrieval.py`).
- Recommendation coverage.
- Top-K diversity.
- Popularity baseline comparison.
- Content-based baseline comparison.

The goal of these metrics is reproducible comparison between artifacts or strategies, not a claim of state-of-the-art recommendation quality.

## Artifacts

Current serving artifacts live under `services/reco-api/models/`:

- `content_embeddings.npz`: movie content embedding matrix (32M catalog cap).
- `content_index.json`: movie identifier to embedding row mapping.
- `catalog_movies.csv`: served movie catalog (search, seeds, scoring).
- `serving_stats.json`: precomputed popularity and user/item counts for startup.
- `item_factors_svd.npz` (optional until M2): truncated-SVD item factors aligned to embedding row order.
- `item_neighbors.json` (optional until M2): item–item co-rating neighbors (top 50 per movie).

The current product UI uses Seed Set recommendations driven by content similarity only until Phase 1 fusion is wired in serving (M2).

## Limitations

- Movie metadata is sparse: content embeddings are built from title and genre text only.
- The public product flow is seed-based and content-signal driven, so Hybrid Score language must be used carefully.
- The served catalog is a popularity-filtered subset of MovieLens 32M, not the full 87k-movie metadata file.
- There is no online learning, personalization feedback loop, or formal A/B testing in the current system.
- RAG explanations describe an existing Recommendation List; they do not choose rankings.

## Risks

- Offline fusion metrics must use the same catalog and held-out protocol as serving before claiming product gains.
- Content-only seed recommendations may overfit to genre/title similarity and miss collaborative taste signals.
- Public demos must avoid committing or exposing provider API keys.
- RAG explanations can become misleading if they are allowed to use unsupported movie facts instead of structured evidence.
- Artifact versioning is still manual until a future Model Registry phase is implemented.
