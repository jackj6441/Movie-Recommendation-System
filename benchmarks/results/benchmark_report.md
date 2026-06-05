# API Benchmark Report

- Base URL: `mock://local`
- Environment: `local`
- Timestamp: `2026-06-05T00:50:45.697016+00:00`
- Requests per endpoint: `5`
- Ranking mode: `multi_retriever_fusion`
- Fusion ready: `True` (svd=`False`, item_cf=`False`)

| Endpoint | Success rate | p50 ms | p95 ms | p99 ms | Timeout s | Requests |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GET /healthz | 1.00 | 0.000 | 0.001 | 0.001 | 10 | 5 |
| GET /metrics | 1.00 | 0.000 | 0.000 | 0.000 | 10 | 5 |
| POST /recommendations | 1.00 | 0.000 | 0.000 | 0.000 | 60 | 5 |
| POST /explanations | 1.00 | 0.000 | 0.000 | 0.000 | 60 | 5 |
| POST /rag/chat | 1.00 | 0.000 | 0.000 | 0.000 | 15 | 5 |
