# Training

Offline scripts build serving artifacts under `services/reco-api/models/`.

## Build content embeddings

```bash
python training/build_content_embeddings.py --device mps
```

## Build serving stats

```bash
python training/build_serving_stats.py
```

## Build SVD item factors (Phase 1 retriever)

Uses the same catalog as `content_embeddings.npz` (row order). Run on the full
MovieLens ratings file that matches your catalog (32M for the committed ~23k catalog):

```bash
python training/build_svd_factors.py \
  --ratings_csv ml-32m/ratings.csv \
  --rank 64
```

Output: `services/reco-api/models/item_factors_svd.npz` (`movie_ids`, `factors`).

## Build item–item neighbors (item-CF retriever)

```bash
python training/build_item_neighbors.py \
  --ratings_csv ml-32m/ratings.csv \
  --top_k 50
```

Output: `services/reco-api/models/item_neighbors.json` (movie id → `[[neighbor_id, score], ...]`).

Smoke on the committed sample:

```bash
python training/build_svd_factors.py --ratings_csv data/ml-32m-sample/ratings.csv
python training/build_item_neighbors.py --ratings_csv data/ml-32m-sample/ratings.csv
```

Commit both artifacts after a full 32M run alongside the content embeddings.

## Phase 2: LightGBM Lambdarank

Build graded-relevance training rows (same seed-held-out protocol as `eval_fusion`) and train:

```bash
python training/train_lambdarank.py \
  --ratings ml-32m/ratings.csv \
  --movies services/reco-api/models/catalog_movies.csv \
  --max-users 2000
```

Outputs:

- `services/reco-api/models/ltr_model.txt`
- `services/reco-api/models/ltr_meta.json`

Enable in serving (default remains Phase 1 fusion):

```bash
export RANKING_MODE=ltr
```

Evaluate:

```bash
python evaluation/eval_ltr.py --max-users 100 --compare-fusion
```

On macOS, LightGBM may require OpenMP: `brew install libomp` if import fails.

## Build poster and movie details lookup (local only)

Extract MovieLens 32M `links.csv` (not committed) and set a TMDB API key:

```bash
# Credentials in repo-root .env are loaded automatically when present.
python training/build_poster_lookup.py \
  --links ml-32m/links.csv \
  --catalog services/reco-api/models/catalog_movies.csv
```

Outputs:

- `services/reco-api/models/poster_urls.json`
- `services/reco-api/models/poster_meta.json`
- `services/reco-api/models/movie_details.json` (overview + `tmdb_id` for watch links)
- `services/reco-api/models/movie_details_meta.json`

Commit all artifacts after a successful run. Use `--resume` to continue a partial build, or `--limit 50` for a smoke test.
