# Training

## Dry run (data pipeline)

```bash
python training/train_ncf.py --dry_run
```

Optional: set `RATINGS_CSV_PATH` if your dataset is in a custom location.

Explicit vs implicit:
This pipeline uses explicit ratings regression (predict 0.5–5.0 values).
Implicit mode would binarize feedback and add negative sampling.
`num_neg` is ignored in explicit mode.

## CPU training (example)

```bash
python training/train_ncf.py --epochs 1
```

## Gradient accumulation (example)

```bash
python training/train_ncf.py --epochs 1 --grad_accum 4
```

## Export ONNX

```bash
python training/export_onnx.py
```

## Build content embeddings

```bash
python training/build_content_embeddings.py --device mps
```

## Build poster lookup (local only)

Extract MovieLens 32M `links.csv` (not committed) and set a TMDB API key:

```bash
# Credentials in repo-root .env (see .env.example) are loaded automatically.
python training/build_poster_lookup.py \
  --links ml-32m/links.csv \
  --catalog services/reco-api/models/catalog_movies.csv
```

Outputs:

- `services/reco-api/models/poster_urls.json`
- `services/reco-api/models/poster_meta.json`

Commit both artifacts after a successful run. Use `--resume` to continue a partial build, or `--limit 50` for a smoke test.
