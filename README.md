# AI-Powered Movie Recommendation System

Monorepo skeleton for a hybrid movie recommendation system (NCF + Transformer content embeddings).

## Structure

- `services/reco-api`: FastAPI + ONNX Runtime + Redis serving service (placeholder).
- `training`: PyTorch Lightning training pipeline (placeholder).
- `web`: React + D3 dashboard (placeholder).
- `infra`: Docker Compose, Nginx, and deployment assets (placeholder).
- `docs`: PRD, architecture notes, and API documentation (placeholder).

## Next steps

1. Add minimal FastAPI app and health checks in `services/reco-api`.
2. Add training scripts and data prep in `training`.
3. Add frontend scaffold in `web`.
4. Add docker-compose and runtime configs in `infra`.
5. Expand docs in `docs`.

## Local Dev

```bash
docker compose -f infra/docker-compose.yml up --build
```

Open:

- http://localhost:3000
- http://localhost:8000/healthz
