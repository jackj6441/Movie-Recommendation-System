# AI-Powered Movie Recommendation System

Monorepo for a hybrid movie recommendation system (NCF + Transformer content embeddings).

## Structure

- `services/reco-api`: FastAPI + ONNX Runtime + Redis serving service.
- `training`: PyTorch Lightning training + export utilities.
- `web`: React + D3 dashboard (wizard UI).
- `infra`: Docker Compose for local development.
- `docs`: PRD, architecture notes, and API documentation.

## Product Flow

1. Select 0–3 genres.
2. Pick 1–5 seed movies (search or recommended seeds).
3. Get top-10 recommendations + explanation.

## Local Dev

```bash
docker compose -f infra/docker-compose.yml up --build
```

Open:

- http://localhost:3000
- http://localhost:8000/healthz

## API Quickstart

```bash
curl "http://localhost:8000/movies/search?q=toy"
curl -X POST http://localhost:8000/recommendations -H "Content-Type: application/json" -d '{"seeds":[1,2,3,4,5]}'
curl -X POST http://localhost:8000/explanations -H "Content-Type: application/json" -d '{"seeds":[1,2,3,4,5]}'
```
