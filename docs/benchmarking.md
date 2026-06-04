# Benchmarking

Measure the recommendation API from a local or remote deployment. The harness sends HTTP requests to core product endpoints and writes JSON/Markdown reports. RAG behavior is not modified here—benchmarks only observe latency and success rate.

## Command

```bash
python benchmarks/benchmark_api.py \
  --base-url http://localhost:8000 \
  --requests 10 \
  --output-dir benchmarks/results \
  --environment local
```

Fusion ranking scans the full catalog for content/SVD channels, so `/recommendations` and `/explanations` use **60s** per-request timeouts by default (override with `--timeout 90` for all endpoints).

Sync portfolio evidence (benchmark p95 + optional fusion eval metrics):

```bash
python benchmarks/benchmark_api.py \
  --base-url http://localhost:8000 \
  --requests 20 \
  --environment local \
  --sync-evidence
```

Requires `evaluation/results/fusion_metrics.json` only when you want `recall_at_10` / `ndcg_at_24` copied into `services/reco-api/evidence/system_evidence.json`.

## EC2

```bash
python benchmarks/benchmark_api.py \
  --base-url http://<ec2-public-ip>:8000 \
  --requests 10 \
  --output-dir benchmarks/results \
  --environment ec2 \
  --sync-evidence
```

## Endpoints

| Endpoint | Notes |
|----------|--------|
| `GET /healthz` | Captured once as `serving` snapshot (`ranking_mode`, `fusion_ok`, …) |
| `GET /metrics` | Prometheus text; success = HTTP 200 |
| `POST /recommendations` | Seed payload `[1,2,3]`; measures fusion path |
| `POST /explanations` | Same ranker as recommendations (duplicate call today) |
| `POST /rag/explanations` | Mock RAG by default; 15s timeout |

Stable POST body:

```json
{"seeds": [1, 2, 3], "shuffle": false}
```

## Artifacts

- `benchmarks/results/benchmark_report.json`
- `benchmarks/results/benchmark_report.md`

JSON includes `serving` from `/healthz` plus per-endpoint latency percentiles.

## Metrics per endpoint

- `success_rate`, `p50_ms`, `p95_ms`, `p99_ms`, `mean_ms`, `timeout_sec`

Use mock RAG (`RAG_PROVIDER=mock`) for public benchmark runs to avoid provider keys and cost.

## Full offline + benchmark pipeline

```bash
python evaluation/eval_fusion.py --max-users 100
python evaluation/tune_fusion_weights.py --quick   # or full grid on 32M
python benchmarks/benchmark_api.py --base-url http://localhost:8000 --requests 20 --sync-evidence
python evaluation/build_report.py
```
