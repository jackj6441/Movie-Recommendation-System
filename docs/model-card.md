# Model Card: Movie Recommendation System

## Dataset

- Product catalog and content embeddings: MovieLens **32M** (`ml-32m`), movies with at least **20** ratings (~23k titles in `catalog_movies.csv`).
- Offline training and NCF evaluation may still reference `ml-latest-small` until a full 32M NCF retrain is committed.
- Required serving files: `catalog_movies.csv`, `content_embeddings.npz`, `content_index.json`, `serving_stats.json`.
- Full `ml-32m/ratings.csv` is used offline only (not loaded at API startup).
- Dataset versioning is currently file-based. A future Model Registry phase should record a formal dataset version with each model artifact.

## Split Strategy

- The NCF rating model uses per-user chronological splitting.
- Users with at least three ratings contribute earlier interactions to training, the second-to-last interaction to validation, and the last interaction to test.
- The evaluation harness uses a per-user held-out interaction for rating RMSE and retrieval-style ranking checks.

## Metrics

The evaluation harness is expected to report:

- RMSE for the ONNX NCF rating model.
- Recall@K for Seed Set recommendation retrieval.
- NDCG@K for Seed Set recommendation retrieval.
- Recommendation coverage.
- Top-K diversity.
- Popularity baseline comparison.
- Content-based baseline comparison.

The goal of these metrics is reproducible comparison between artifacts or strategies, not a claim of state-of-the-art recommendation quality.

## Artifacts

Current serving artifacts live under `services/reco-api/models/`:

- `ncf.onnx`: exported NCF rating model for ONNX Runtime.
- `metadata.json`: user and movie index mappings for the NCF model.
- `content_embeddings.npz`: movie content embedding matrix (32M catalog cap).
- `content_index.json`: movie identifier to embedding row mapping.
- `catalog_movies.csv`: served movie catalog (search, seeds, scoring).
- `serving_stats.json`: precomputed popularity and user/item counts for startup.

The current product UI uses Seed Set recommendations driven by Content Signal. The NCF / ONNX model is available through legacy/debug paths and the model evaluation harness unless a later phase wires it into product ranking.

## Limitations

- Movie metadata is sparse: content embeddings are built from title and genre text only.
- The public product flow is seed-based and content-signal driven, so Hybrid Score language must be used carefully.
- The served catalog is a popularity-filtered subset of MovieLens 32M, not the full 87k-movie metadata file.
- There is no online learning, personalization feedback loop, or formal A/B testing in the current system.
- RAG explanations describe an existing Recommendation List; they do not choose rankings.

## Risks

- Evaluation results can be overstated if the product path and NCF path are not clearly separated.
- Content-only seed recommendations may overfit to genre/title similarity and miss collaborative taste signals.
- Public demos must avoid committing or exposing provider API keys.
- RAG explanations can become misleading if they are allowed to use unsupported movie facts instead of structured evidence.
- Artifact versioning is still manual until a future Model Registry phase is implemented.
