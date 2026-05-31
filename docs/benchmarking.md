# Benchmarking

Use the benchmark harness to measure the recommendation API from a local or remote deployment. The script sends real HTTP requests to the core product endpoints and writes both machine-readable and human-readable reports.

## Command

```bash
python benchmarks/benchmark_api.py \
  --base-url http://localhost:8000 \
  --requests 10 \
  --output-dir benchmarks/results \
  --environment local
```

For EC2, replace `--base-url` with the public API URL:

```bash
python benchmarks/benchmark_api.py \
  --base-url http://<ec2-public-ip>:8000 \
  --requests 10 \
  --output-dir benchmarks/results \
  --environment ec2
```

## Endpoints

The benchmark covers:

- `GET /healthz`
- `POST /recommendations`
- `POST /explanations`
- `POST /rag/explanations`

The POST endpoints use a stable Seed Set payload:

```json
{"seeds": [1, 2, 3], "shuffle": false}
```

## Artifacts

The script writes:

- `benchmark_report.json`
- `benchmark_report.md`

The JSON report is intended for automation and future comparison. The Markdown report is intended for README summaries, interview evidence, and manual review.

## Metrics

Each endpoint report includes:

- `request_count`: number of requests sent to the endpoint.
- `success_rate`: fraction of requests that returned a 2xx response.
- `p50`: median latency in milliseconds.
- `p95`: 95th percentile latency in milliseconds.
- `p99`: 99th percentile latency in milliseconds.
- `mean_ms`: average latency in milliseconds.

The report also records the target `base_url`, timestamp, and environment label so local and EC2 runs can be compared without guessing where the numbers came from.

## Notes

Use mock RAG mode for public benchmark runs unless you intentionally want to measure an external provider. This avoids uncontrolled provider cost and removes provider-key requirements from portfolio demos.
