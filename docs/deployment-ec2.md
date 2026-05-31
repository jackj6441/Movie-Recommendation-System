# AWS EC2 Deployment Guide

This guide documents the first public Docker Compose demo for the movie recommendation system.

The goal is a simple ML Infra portfolio deployment, not a hardened production environment. The first version uses an AWS EC2 public IP and exposed service ports so recruiters and interviewers can open the UI, `/healthz`, and `/metrics`.

## Deployment Shape

- Platform: AWS EC2
- Runtime: Docker Compose
- Services:
  - Redis on port `6379`
  - FastAPI recommendation API on port `8000`
  - React/Vite web UI on port `3000`
- Public demo RAG mode: `RAG_PROVIDER=mock`
- Public API base for frontend: `PUBLIC_API_BASE=http://<ec2-public-ip>:8000`

Do not commit real .env files, provider keys, SSH keys, or AWS credentials.

## EC2 Instance Assumptions

Use a small Linux EC2 instance for the first demo. Ubuntu LTS is the easiest path.

Minimum practical setup:

- 2 vCPU
- 4 GB RAM
- 20 GB disk
- inbound SSH from your IP only
- inbound HTTP demo ports from your expected reviewer audience

## Security Group

Configure the EC2 security group before starting the public demo.

For the first public demo, open:

| Port | Purpose | Source |
| --- | --- | --- |
| `22` | SSH | Your IP only |
| `3000` | Web UI | Public or restricted reviewer IPs |
| `8000` | API, `/healthz`, `/metrics` | Public or restricted reviewer IPs |

Do not expose Redis port `6379` publicly. Redis is only needed by the Docker network.

## Install Docker

On the EC2 host:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
docker --version
docker compose version
```

## Clone and Configure

```bash
git clone https://github.com/jackj6441/Movie-Recommendation-System.git
cd Movie-Recommendation-System
```

Create a local `.env` file for the EC2 shell session or export variables directly:

```bash
export PUBLIC_API_BASE=http://<ec2-public-ip>:8000
export CORS_ALLOW_ORIGINS=http://<ec2-public-ip>:3000
export RAG_PROVIDER=mock
```

Use mock RAG for the public demo unless you intentionally want to benchmark an external provider. This avoids uncontrolled provider cost and avoids public demo dependency on a secret.

## Start the Stack

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

Check containers:

```bash
docker compose -f infra/docker-compose.yml ps
```

## Validate the Demo

From your local machine or the EC2 host:

```bash
curl http://<ec2-public-ip>:8000/healthz
curl http://<ec2-public-ip>:8000/metrics
```

Open the UI:

```text
http://<ec2-public-ip>:3000
```

Manual product validation:

1. Open the web UI.
2. Select zero to three genres.
3. Select one to five Seed Movies.
4. Request recommendations.
5. Confirm the Recommendation List appears.
6. Confirm the mock RAG Explanation appears.

API validation:

```bash
curl -X POST http://<ec2-public-ip>:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"seeds":[1,2,3],"shuffle":false}'

curl -X POST http://<ec2-public-ip>:8000/rag/explanations \
  -H "Content-Type: application/json" \
  -d '{"seeds":[1,2,3],"shuffle":false}'
```

Benchmark validation:

```bash
python benchmarks/benchmark_api.py \
  --base-url http://<ec2-public-ip>:8000 \
  --requests 10 \
  --output-dir benchmarks/results \
  --environment ec2
```

## Update Deployment

```bash
git pull
docker compose -f infra/docker-compose.yml up --build -d
```

## Restart

```bash
docker compose -f infra/docker-compose.yml restart
```

## Stop

```bash
docker compose -f infra/docker-compose.yml down
```

## Logs

```bash
docker compose -f infra/docker-compose.yml logs -f reco-api
docker compose -f infra/docker-compose.yml logs -f web
docker compose -f infra/docker-compose.yml logs -f redis
```

## Expected Public Behavior

- `GET /healthz` shows readiness status and dependency health.
- `GET /metrics` shows Prometheus-style observability metrics.
- Public RAG uses `RAG_PROVIDER=mock`.
- The UI talks to `PUBLIC_API_BASE`, not browser-local `localhost`.
- The API allows the public UI origin through `CORS_ALLOW_ORIGINS`.
- Real provider API keys are not required for the public demo.

## Known Limits

- This first version uses public IP and ports, not domain or HTTPS.
- There is no autoscaling.
- Redis persistence is local to the EC2 host volume.
- This guide intentionally avoids committing secrets or provider credentials.
