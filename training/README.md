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

## Build poster lookup (local only)

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

Commit both artifacts after a successful run. Use `--resume` to continue a partial build, or `--limit 50` for a smoke test.
