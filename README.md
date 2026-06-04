# Movie Recommendation ML Platform

Production-style ML recommendation platform for ML Infra / MLOps portfolio review.

This repo demonstrates the system path:

```text
training -> evaluation -> serving -> explanation -> monitoring -> deployment
```

It packages a movie recommender as an operational ML system: offline artifact builds, FastAPI serving, React UI, RAG-style explanations, Prometheus-style metrics, benchmark reports, CI, and an AWS EC2 Docker Compose demo.

## Live Demo

- UI: http://34.228.75.214:3000
- API readiness: http://34.228.75.214:8000/healthz
- Runtime metrics: http://34.228.75.214:8000/metrics
- System evidence: http://34.228.75.214:8000/system/evidence
- Public demo RAG mode: mock provider by default, no public API key required.

## Project Evidence

- Evaluation report: `evaluation/results/eval_report.md`
  - Product retrieval (MovieLens 32M catalog, min 20 ratings): Recall@K `0.04`, NDCG@K `0.0187`, coverage `0.0171`, top-K diversity `0.63`
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
  -> content + SVD + item-CF + serving stats (offline)
  -> FastAPI four-retriever fusion (Top-24)
  -> RAG explanation layer (mock by default)
  -> React UI + System Evidence Dashboard
  -> /healthz + /metrics + eval/benchmark artifacts
  -> AWS EC2 Docker Compose demo
```

## Current Product Flow

1. Select 0-3 genres.
2. Pick 1-5 seed movies from search or recommended seeds.
3. Generate top-10 recommendations.
4. Inspect explanation, score breakdown, health, metrics, and benchmark evidence.

Important model truth: the UI uses Seed Set recommendations via multi-retriever fusion (content, SVD, item-CF, popularity). Place `item_factors_svd.npz` and `item_neighbors.json` in `services/reco-api/models/` (built from MovieLens 32M) for full channel coverage.

## Stack

- Backend: FastAPI, NumPy, content embeddings.
- Training: MovieLens preprocessing, SentenceTransformer embeddings, serving stats.
- Frontend: React, TypeScript, Vite.
- Infra: Docker Compose, GitHub Actions CI, AWS EC2.
- Observability: `GET /healthz`, `GET /metrics`, benchmark artifacts.
- Portfolio evidence: `GET /system/evidence` and the System Evidence Dashboard.

## Repository Structure

- `services/reco-api`: FastAPI seed-set serving with Phase 1 multi-retriever fusion.
- `training`: MovieLens preprocessing, embeddings, SVD/item-CF artifact builds.
- `evaluation`: reproducible model and retrieval evaluation harness.
- `benchmarks`: API benchmark CLI and committed benchmark reports.
- `web`: React + D3 recommendation dashboard.
- `infra`: Docker Compose local and EC2 demo infrastructure.
- `docs`: PRDs, architecture, API docs, deployment guide, and model card.

## Posters (optional offline build)

Movie posters are served from committed `services/reco-api/models/poster_urls.json`. To rebuild from MovieLens 32M links and TMDB:

```bash
export TMDB_API_KEY=your_key_here
python training/build_poster_lookup.py --links ml-32m/links.csv
```

See `training/README.md` for details. Docker runtime does not need `TMDB_API_KEY`.

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
python evaluation/eval_retrieval.py
python evaluation/eval_fusion.py --max-users 100
python evaluation/tune_fusion_weights.py --quick
python evaluation/build_report.py
```

## Benchmark

```bash
python benchmarks/benchmark_api.py --base-url http://localhost:8000 --requests 20 --environment local --sync-evidence
```

See `docs/benchmarking.md` and `evaluation/README.md`.

## Deployment Notes

For EC2, set non-secret public demo configuration before starting Docker Compose:

```bash
export PUBLIC_API_BASE=http://<ec2-public-ip>:8000
export CORS_ALLOW_ORIGINS=http://<ec2-public-ip>:3000
export RAG_PROVIDER=mock
docker compose -f infra/docker-compose.yml up --build -d
```

Do not commit `.env` files, real provider API keys, or other secrets.
