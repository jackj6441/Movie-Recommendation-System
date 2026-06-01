# Movie Recommendation ML Platform

Production-style ML recommendation platform for ML Infra / MLOps portfolio review.

This repo demonstrates the system path:

```text
training -> evaluation -> export -> serving -> caching -> explanation -> monitoring -> deployment
```

It packages a movie recommender as an operational ML system: PyTorch Lightning training, ONNX Runtime serving, Redis caching, FastAPI APIs, React/D3 UI, RAG-style explanations, Prometheus-style metrics, benchmark reports, CI, and an AWS EC2 Docker Compose demo.

## Live Demo

- UI: http://34.228.75.214:3000
- API readiness: http://34.228.75.214:8000/healthz
- Runtime metrics: http://34.228.75.214:8000/metrics
- System evidence: http://34.228.75.214:8000/system/evidence
- Public demo RAG mode: mock provider by default, no public API key required.

## Project Evidence

- Evaluation report: `evaluation/results/eval_report.md`
  - RMSE: `3.1438`
  - Recall@K: `0.05`
  - NDCG@K: `0.0258`
  - Coverage: `0.0287`
  - Top-K diversity: `0.5997`
- Benchmark report: `benchmarks/results/benchmark_report.md`
  - `GET /healthz`
  - `GET /metrics`
  - `GET /system/evidence`
  - `POST /recommendations`
  - `POST /explanations`
  - `POST /rag/explanations`
- System Evidence Dashboard: available from the UI tab, showing serving health, evaluation quality, current vs popularity baseline, latency benchmark, RAG safety, and AWS EC2 deployment proof.
- Model documentation: `docs/model-card.md`
- EC2 deployment guide: `docs/deployment-ec2.md`
- API contract: `docs/api.md`

## Architecture

```text
MovieLens data
  -> PyTorch Lightning training
  -> ONNX export + content embeddings
  -> FastAPI serving
  -> Redis cache
  -> RAG explanation layer
  -> React/D3 UI
  -> /healthz + /metrics + benchmark reports
  -> AWS EC2 Docker Compose demo
```

## Current Product Flow

1. Select 0-3 genres.
2. Pick 1-5 seed movies from search or recommended seeds.
3. Generate top-10 recommendations.
4. Inspect explanation, score breakdown, health, metrics, and benchmark evidence.

Important model truth: the current UI uses Seed Set recommendations driven by Content Signal. The NCF / ONNX model remains available through legacy/debug paths and the evaluation harness unless a later phase wires it into product ranking.

## Stack

- Backend: FastAPI, ONNX Runtime, Redis.
- Training: PyTorch Lightning, MovieLens preprocessing, ONNX export.
- Frontend: React, TypeScript, D3, Vite.
- Infra: Docker Compose, GitHub Actions CI, AWS EC2.
- Observability: `GET /healthz`, `GET /metrics`, benchmark artifacts.
- Portfolio evidence: `GET /system/evidence` and the System Evidence Dashboard.

## Repository Structure

- `services/reco-api`: FastAPI + ONNX Runtime + Redis serving service.
- `training`: PyTorch Lightning training, export, and embedding utilities.
- `evaluation`: reproducible model and retrieval evaluation harness.
- `benchmarks`: API benchmark CLI and committed benchmark reports.
- `web`: React + D3 recommendation dashboard.
- `infra`: Docker Compose local and EC2 demo infrastructure.
- `docs`: PRDs, architecture, API docs, deployment guide, and model card.

## Local Development

```bash
docker compose -f infra/docker-compose.yml up --build
```

Open:

- http://localhost:3000
- http://localhost:8000/healthz
- http://localhost:8000/metrics

## API Quickstart

```bash
curl "http://localhost:8000/movies/search?q=toy"
curl -X POST http://localhost:8000/recommendations -H "Content-Type: application/json" -d '{"seeds":[1,2,3,4,5]}'
curl -X POST http://localhost:8000/explanations -H "Content-Type: application/json" -d '{"seeds":[1,2,3,4,5]}'
curl -X POST http://localhost:8000/rag/explanations -H "Content-Type: application/json" -d '{"seeds":[1,2,3,4,5]}'
```

## Reproducible Evaluation

```bash
python evaluation/eval_model.py --model services/reco-api/models/ncf.onnx
python evaluation/eval_retrieval.py
python evaluation/build_report.py
```

## Benchmark

```bash
python benchmarks/benchmark_api.py --base-url http://localhost:8000 --requests 20 --environment local
```

## Deployment Notes

For EC2, set non-secret public demo configuration before starting Docker Compose:

```bash
export PUBLIC_API_BASE=http://<ec2-public-ip>:8000
export CORS_ALLOW_ORIGINS=http://<ec2-public-ip>:3000
export RAG_PROVIDER=mock
docker compose -f infra/docker-compose.yml up --build -d
```

Do not commit `.env` files, real provider API keys, or other secrets.
