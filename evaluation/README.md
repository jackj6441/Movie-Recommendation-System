# Evaluation

## Content-only baseline

```bash
python evaluation/eval_retrieval.py --max-users 100 --k 10
```

## Phase 1 fusion (@10 and @24)

Uses the same offline pipeline as `reco-api` serving (four retrievers + weighted fusion):

```bash
python evaluation/eval_fusion.py \
  --ratings data/ml-32m-sample/ratings.csv \
  --movies services/reco-api/models/catalog_movies.csv \
  --max-users 100
```

Output: `evaluation/results/fusion_metrics.json` with `recall_at_10`, `recall_at_24`, `ndcg_at_10`, `ndcg_at_24`.

## Tune fusion weights

Grid search on the 4-channel simplex (pop capped at 0.10) and write `services/reco-api/models/fusion_weights.json`:

```bash
python evaluation/tune_fusion_weights.py \
  --ratings ml-32m/ratings.csv \
  --max-users 200 \
  --objective recall_at_10
```

Smoke:

```bash
python evaluation/tune_fusion_weights.py --quick --max-users 20
```

Report: `evaluation/results/fusion_tune.json`.

## Phase 2 LTR (@10 and @24)

Requires a trained `ltr_model.txt`:

```bash
python evaluation/eval_ltr.py --max-users 100 --compare-fusion
```

## Combined report

```bash
python evaluation/build_report.py \
  --retrieval-metrics evaluation/results/retrieval_metrics.json \
  --fusion-metrics evaluation/results/fusion_metrics.json \
  --fusion-tune evaluation/results/fusion_tune.json
```
