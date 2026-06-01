# Resume Bullets: ML Infra / MLOps Portfolio

Use these as source bullets, then tune numbers and wording for the target role.

- Built and deployed an end-to-end recommendation platform with PyTorch Lightning training, ONNX Runtime serving, Redis caching, FastAPI APIs, React/D3 UI, Docker Compose, and an AWS EC2 live demo.
- Implemented reproducible ML evaluation with ONNX RMSE, Recall@K, NDCG@K, recommendation coverage, diversity metrics, baseline comparisons, and committed JSON/Markdown evaluation reports.
- Added production-style observability with `GET /healthz`, `GET /metrics`, the System Evidence Dashboard, Prometheus-style request/cache/RAG metrics, API latency benchmarks, and CI checks for backend tests, frontend tests, frontend build, and Docker builds.
- Designed safe RAG explanation serving with schema validation, deterministic fallback behavior, request IDs, cache-aware evidence hashing, mock RAG public demo mode, and secret-safe external provider configuration.

## Interview Positioning

Strong framing:

```text
I used the project to demonstrate operational ML readiness: reproducible evaluation, artifact-aware serving, observability, CI, Dockerized deployment, and a live EC2 demo.
```

Avoid overstating the recommender model:

```text
The current product UI uses Seed Set recommendations driven by Content Signal. The NCF / ONNX model is preserved in legacy/debug paths and evaluated through the harness unless a later phase wires it into product ranking.
```

## Public Demo Safety

Public demo should use `RAG_PROVIDER=mock`. Real provider keys must stay in backend runtime environment variables. Do not commit `.env` files, API keys, SSH keys, or AWS credentials.
