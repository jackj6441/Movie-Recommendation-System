# Runbook: Movie Recommendation ML Platform

This runbook is for local development and the AWS EC2 Docker Compose demo.

## Startup

Local:

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

EC2 public demo:

```bash
export PUBLIC_API_BASE=http://<ec2-public-ip>:8000
export CORS_ALLOW_ORIGINS=http://<ec2-public-ip>:3000
export RAG_PROVIDER=mock
docker compose -f infra/docker-compose.yml up --build -d
```

Expected services:

```bash
docker compose -f infra/docker-compose.yml ps
```

- `redis`
- `reco-api`
- `web`

## Health Checks

Use `GET /healthz` for readiness:

```bash
curl http://localhost:8000/healthz
curl http://<ec2-public-ip>:8000/healthz
```

Healthy output should report:

- `status: ok`
- `redis_ok: true`
- `onnx_ok: true`
- `metadata_ok: true`
- `model_version`

Use `GET /metrics` for observability:

```bash
curl http://localhost:8000/metrics
curl http://<ec2-public-ip>:8000/metrics
```

Expected metrics include request counts, latency sums, cache events, RAG outcomes, fallback reasons, and provider mode.

## Logs

```bash
docker compose -f infra/docker-compose.yml logs -f reco-api
docker compose -f infra/docker-compose.yml logs -f web
docker compose -f infra/docker-compose.yml logs -f redis
```

Useful targeted checks:

```bash
docker compose -f infra/docker-compose.yml logs --tail=120 reco-api
docker compose -f infra/docker-compose.yml exec -T web printenv VITE_API_BASE
docker compose -f infra/docker-compose.yml exec -T reco-api printenv CORS_ALLOW_ORIGINS
```

## Restart

Restart one service:

```bash
docker compose -f infra/docker-compose.yml restart reco-api
docker compose -f infra/docker-compose.yml restart web
```

Rebuild after code or environment changes:

```bash
docker compose -f infra/docker-compose.yml up --build -d --force-recreate reco-api web
```

Stop the stack without deleting containers:

```bash
docker compose -f infra/docker-compose.yml stop
```

Stop and remove containers and network while keeping volumes:

```bash
docker compose -f infra/docker-compose.yml down
```

## Rollback

Rollback to a previous known-good commit:

```bash
git log --oneline -5
git checkout <known-good-commit>
docker compose -f infra/docker-compose.yml up --build -d --force-recreate
```

For normal main-branch recovery:

```bash
git checkout main
git pull --ff-only
docker compose -f infra/docker-compose.yml up --build -d --force-recreate
```

## Secret Handling

- Do not commit `.env`, `.env.*`, provider API keys, SSH private keys, or AWS credentials.
- Public EC2 demo should use `RAG_PROVIDER=mock`.
- Real provider keys must stay in the runtime environment only.
- Never expose provider keys in frontend code, Docker image layers, logs, screenshots, or README examples.

## Common Failure Modes

### Frontend Loads but Recommendations Do Not Appear

Check browser/API wiring:

```bash
curl http://<ec2-public-ip>:3000/src/App.tsx | grep VITE_API_BASE
curl -i -X OPTIONS \
  -H "Origin: http://<ec2-public-ip>:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  http://<ec2-public-ip>:8000/recommendations
```

Expected: `VITE_API_BASE` points to the EC2 API and the CORS preflight returns `200 OK`.

### Backend Is Unhealthy

Run:

```bash
curl http://<ec2-public-ip>:8000/healthz
docker compose -f infra/docker-compose.yml logs --tail=120 reco-api
```

Common causes:

- missing model files under `services/reco-api/models`
- missing `ml-latest-small` dataset files
- Redis container is down
- wrong bind mount path

### RAG Explanation Unavailable

For public demo, keep:

```bash
export RAG_PROVIDER=mock
```

If using an external provider, verify the runtime key exists inside the backend environment and do not commit it.

### Redis Issues

The API should still expose `/healthz` with degraded Redis state if Redis is down. Restart Redis:

```bash
docker compose -f infra/docker-compose.yml restart redis
```

### EC2 Port Is Not Reachable

Check AWS Security Group inbound rules:

- `22` from your IP only.
- `3000` from `0.0.0.0/0` for public UI.
- `8000` from `0.0.0.0/0` for demo API.
- Do not expose Redis `6379` publicly.
