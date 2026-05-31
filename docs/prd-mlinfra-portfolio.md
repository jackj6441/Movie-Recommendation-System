# PRD: ML Infra Portfolio Upgrade

## Overview

Upgrade the current movie recommendation project into a production-style ML system portfolio for ML Infra / MLOps roles.

The project already has a training pipeline, ONNX serving, Redis caching, RAG explanations, a React + D3 UI, and Docker Compose. This PRD defines a one-month upgrade plan that turns those pieces into interview-ready evidence: reproducible evaluation, operational metrics, CI, benchmarks, deployment documentation, and an AWS EC2 live demo.

The goal is not to build a more complex recommender algorithm. The goal is to prove that the system can be trained, evaluated, served, observed, benchmarked, deployed, and explained in a way that resembles a real ML platform.

## Goals

- Position the project for ML Infra / MLOps interviews, not only general full-stack or notebook-based ML demos.
- Create interview-ready evidence that can be shown through GitHub docs, benchmark reports, API endpoints, and a live EC2 deployment.
- Add a reproducible evaluation harness for model and recommendation strategy comparison.
- Add CI checks for backend tests, frontend tests, frontend build, and Docker builds.
- Add runtime observability through a Prometheus-style `GET /metrics` endpoint.
- Add benchmark artifacts for local and EC2 performance comparisons.
- Deploy the project on AWS EC2 with Docker Compose using mock RAG by default.
- Keep existing product endpoints stable while adding operational proof around them.

## Non-Goals

- Do not overhaul the recommendation algorithm in month 1.
- Do not add `POST /recommendations/full` in month 1.
- Do not replace the current product flow.
- Do not make RAG part of ranking.
- Do not expose OpenAI or provider secrets in frontend code or public demo configuration.
- Do not fully implement Model Registry / Artifact Versioning in month 1.
- Do not fully implement Shadow / Canary model comparison in month 1.
- Do not fully implement Reliability / Failure Injection tests in month 1.
- Do not add domain, HTTPS, or production-grade certificate automation for the first EC2 demo.

## Users & Scenarios

- Recruiters and hiring managers: quickly understand why this is more than a standard movie recommender project.
- ML Infra interviewers: inspect reproducibility, serving, observability, CI, benchmarking, and deployment decisions.
- Operators: verify service health, metrics, deployment steps, and expected degraded behavior.
- Maintainers: use the PRD as the source of truth for follow-up implementation tasks.

## Requirements

### Portfolio Packaging

- Rewrite the main README around the system story: training -> evaluation -> export -> serving -> caching -> explanation -> monitoring -> deployment.
- Add or reference an architecture diagram that shows the training, serving, Redis, RAG, frontend, and deployment surfaces.
- Add a live EC2 demo URL once deployed.
- Add direct links or examples for `/healthz` and `/metrics`.
- Add UI screenshots and benchmark summary tables.
- Add `docs/model-card.md` with:
  - dataset and dataset version
  - train/validation/test split strategy
  - model artifacts
  - evaluation metrics
  - known limitations
  - risk notes
- Add `docs/runbook.md` with:
  - local startup
  - EC2 startup
  - health checks
  - log inspection
  - restart and rollback steps
  - secret handling
  - common failure modes
- Add `docs/deployment-ec2.md` with:
  - EC2 instance assumptions
  - Docker and Docker Compose setup
  - security group ports
  - environment configuration
  - deploy and update commands
  - validation commands
- Add `docs/resume-bullets.md` with 3-5 resume bullets tailored to ML Infra / MLOps roles.
- Clearly document the current product truth: seed-based recommendations are driven by Content Signal, while NCF / ONNX is currently used by legacy/debug paths and model evaluation unless later wired into product ranking.

### Evaluation Harness

- Add an `evaluation/` directory with runnable scripts:
  - `evaluation/eval_model.py`
  - `evaluation/eval_retrieval.py`
  - `evaluation/build_report.py`
- Support these commands:
  - `python evaluation/eval_model.py --model services/reco-api/models/ncf.onnx`
  - `python evaluation/eval_retrieval.py`
  - `python evaluation/build_report.py`
- Write outputs to:
  - `evaluation/results/eval_report.json`
  - `evaluation/results/eval_report.md`
- Report at least:
  - RMSE
  - Recall@K
  - NDCG@K
  - recommendation coverage
  - top-K diversity
  - popularity baseline comparison
  - content-based baseline comparison
- The evaluation harness should optimize for reproducible comparison between model or strategy versions, not for claiming state-of-the-art quality.

### Observability

- Add `GET /metrics`.
- Return Prometheus-style text exposition with `text/plain` content type.
- Include at least:
  - request count by endpoint and status
  - request latency buckets or summary values
  - Redis cache hit and miss counts
  - RAG explanation source counts: `rag`, `rag_cache`, `deterministic_fallback`
  - RAG fallback reason counts
  - current RAG provider mode
- Keep `GET /healthz` as the readiness endpoint.
- Document the meaning of each `/healthz` field and how it differs from `/metrics`.

### CI

- Add GitHub Actions checks for:
  - backend pytest
  - frontend Vitest
  - frontend build
  - backend Docker build
  - frontend Docker build
- Pull requests should fail if any required check fails.
- CI should not require real provider API keys.
- CI should use mock RAG mode.

### Benchmarking

- Add a benchmark script that can run against local and EC2 deployments.
- Benchmark at least:
  - `GET /healthz`
  - `POST /recommendations`
  - `POST /explanations`
  - `POST /rag/explanations`
- Produce both machine-readable and human-readable artifacts:
  - JSON report
  - Markdown report
- Reports should include:
  - p50 latency
  - p95 latency
  - p99 latency
  - success rate
  - request count
  - target base URL
  - timestamp
  - environment notes
- The README should reference the latest benchmark summary.

### AWS EC2 Demo

- Deploy Redis, the FastAPI API, and the web app with Docker Compose.
- Use EC2 public IP and service ports for the first version.
- Publicly expose:
  - web UI
  - `/healthz`
  - `/metrics`
- Use mock RAG by default in the public demo.
- Keep real provider API keys out of the public demo and repository.
- Commit only `.env.example` files, never real `.env` files.
- The deployment should be verifiable with documented commands.

## Public Interfaces & Artifacts

- Existing product endpoints remain stable:
  - `POST /recommendations`
  - `POST /explanations`
  - `POST /rag/explanations`
- Add:
  - `GET /metrics`
- New documentation artifacts:
  - `docs/model-card.md`
  - `docs/runbook.md`
  - `docs/deployment-ec2.md`
  - `docs/resume-bullets.md`
- New evaluation artifacts:
  - `evaluation/results/eval_report.json`
  - `evaluation/results/eval_report.md`
- New benchmark artifacts:
  - JSON benchmark report
  - Markdown benchmark report

## Acceptance Criteria

- The main README clearly presents the project as an ML Infra / MLOps portfolio project.
- `docs/model-card.md`, `docs/runbook.md`, `docs/deployment-ec2.md`, and `docs/resume-bullets.md` exist and are written in English.
- The evaluation harness runs from the command line and writes JSON and Markdown reports.
- `GET /metrics` returns Prometheus-style text metrics.
- `/healthz` continues to work and is documented as the readiness endpoint.
- GitHub Actions runs backend tests, frontend tests, frontend build, and Docker builds.
- Benchmarking can run locally and against EC2 and writes JSON and Markdown output.
- The EC2 demo loads the UI through a public URL.
- The EC2 API exposes `/healthz` and `/metrics`.
- The recommendation flow works on EC2.
- Mock RAG explanation works on EC2 without a real provider key.
- No secrets, `.env` files, or provider keys are committed.

## Test Plan

- Backend:
  - Run existing pytest suite.
  - Add tests for `/metrics` response shape and content type.
  - Add tests for RAG fallback counters.
  - Add tests for `/healthz` healthy and degraded behavior where feasible.
- Frontend:
  - Run existing Vitest suite.
  - Run production build.
- Evaluation:
  - Verify `eval_model.py` produces RMSE.
  - Verify `eval_retrieval.py` produces Recall@K, NDCG@K, coverage, diversity, and baseline comparison.
  - Verify `build_report.py` writes JSON and Markdown reports.
- CI:
  - Verify all required checks run without real provider secrets.
- Benchmark:
  - Verify reports include p50, p95, p99, success rate, request count, target URL, timestamp, and environment notes.
- Deployment:
  - Verify EC2 UI, `/healthz`, `/metrics`, and recommendation flow.

## Roadmap

These are explicitly out of scope for month 1 but should be listed as next-phase ML platform upgrades.

### Model Registry / Artifact Versioning

- Add a lightweight registry layout such as:

```text
artifacts/
  movie-reco/
    v0.1.0/
      model.onnx
      metadata.json
      metrics.json
      config.yaml
```

- Track:
  - model name
  - model version
  - ONNX artifact path
  - content artifact paths
  - dataset version
  - train/validation/test split
  - git commit
  - training command
  - export command
  - metrics
  - created time
- Add `GET /model/info` for runtime model introspection.

### Shadow / Canary Model Comparison

- Add configuration such as:

```text
MODEL_VERSION=v0.1.0
SHADOW_MODEL_VERSION=v0.2.0
ENABLE_SHADOW_EVAL=true
```

- Serve main model results to users while evaluating shadow model behavior in the background.
- Track:
  - main model latency
  - shadow model latency
  - top-K overlap
  - disagreement rate
  - shadow error count

### Reliability / Failure Injection Tests

- Add fault scripts for:
  - Redis down
  - RAG timeout
  - model missing
  - invalid model metadata
  - OpenAI key missing
- Document expected behavior in `docs/reliability.md`.
- Use these tests to prove degraded service behavior, health checks, and deterministic fallback.

## Assumptions

- Target role is ML Infra / MLOps Engineer.
- Timeline is one month.
- Repo-facing portfolio docs are written in English.
- Public EC2 demo uses mock RAG by default.
- Real OpenAI provider remains a configurable capability, not a public demo dependency.
- First EC2 version uses public IP and ports, not domain or HTTPS.
- Month 1 prioritizes production credibility and interview evidence over algorithm complexity.
