# API Benchmark Report

- Base URL: `http://127.0.0.1:18000`
- Environment: `local`
- Timestamp: `2026-05-31T21:37:06.556726+00:00`
- Requests per endpoint: `5`

| Endpoint | Success rate | p50 ms | p95 ms | p99 ms | Requests |
| --- | ---: | ---: | ---: | ---: | ---: |
| GET /healthz | 1.00 | 3.632 | 34.461 | 40.570 | 5 |
| POST /recommendations | 1.00 | 5.314 | 65.459 | 77.379 | 5 |
| POST /explanations | 1.00 | 4.976 | 5.787 | 5.907 | 5 |
| POST /rag/explanations | 1.00 | 4.983 | 5.088 | 5.093 | 5 |
