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
