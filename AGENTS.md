# Agent Guide

## Project overview

This repo is an AI-powered movie recommendation system with a FastAPI serving API, offline embedding builds, React dashboard, and Docker Compose local infrastructure.

Primary docs:

- `README.md`: repo structure, product flow, local startup, and API quickstart.
- `RULES.md`: fixed stack, change principles, security rules, and runtime requirements.
- `docs/prd.md`: product goals, non-goals, metrics, and risks.
- `docs/architecture.md`: system components, offline/online data flow, artifacts, cache/config model.
- `docs/api.md`: API contract and examples.

## Communication

- **Reply to the user in Chinese (简体中文)** for explanations, summaries, and status updates unless they ask for another language.

## Working rules

- Before editing, form a complete todolist from the prompt.
- Work on one feature at a time.
- Keep bug fixes minimal. Do not do broad refactors unless explicitly asked.
- Preserve the fixed stack: FastAPI + NumPy fusion serving, offline PyTorch/SentenceTransformer training, React + TypeScript, Docker, AWS EC2.
- Do not commit `.env` files, secrets, or sensitive data. Never log secrets.
- Every service must expose `/healthz`.
- API responses must include `model_version` when returning model-backed results.
- After each meaningful checkpoint, **commit automatically** once tests pass (see `.cursor/rules/auto-commit.mdc`). Do not push unless asked.
- During TDD work, commit after each completed red-green-refactor step once tests pass.
- After changing code, explain the change, especially every new or modified function and why it exists.

## Repo layout

- `services/reco-api`: FastAPI seed-set fusion ranking (`app/retrievers/`, `app/fusion.py`, `app/seed_ranker.py`).
- `training`: Content embeddings, serving stats, SVD factors, item neighbors, poster lookup.
- `evaluation`: `eval_fusion.py`, `tune_fusion_weights.py`, `build_report.py`.
- `benchmarks`: `benchmark_api.py` (+ `--sync-evidence` for portfolio JSON).
- `web`: React + D3 recommendation dashboard.
- `infra`: Docker Compose local development files.
- `docs`: PRD, architecture notes, and API reference.
- `ml-latest-small`: local development dataset.

## Common commands

Local stack:

```bash
docker compose -f infra/docker-compose.yml up --build
```

Training dry run:

Build content embeddings:

```bash
python training/build_content_embeddings.py --device mps
```

Frontend:

```bash
cd web
npm run dev
npm run build
```

## Product and API constraints

- Current product flow: ChatGPT-style chat with genre chips, `POST /rag/chat` (SSE), and embedded recommendation cards (ranking via multi-retriever fusion / optional LTR).
- Product endpoint: `POST /rag/chat`. `POST /recommendations` remains for tests; `POST /explanations` is debug-only.
- Debug endpoint: `GET /debug/similar` (content similarity; not used by the UI).
- Health check is `GET /healthz`.
- Search is case-insensitive substring search by title.
- Seed-based recommendations use four retrievers + weighted fusion (`fusion_weights.json`); optional Phase 2 via `RANKING_MODE=ltr` and `ltr_model.txt`.
- Explanations show `content` and `final` (fusion) scores. RAG module is legacy-shaped; refactor deferred.

## Agent skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `jackj6441/Movie-Recommendation-System`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the default triage label vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo. Read root domain docs if present and use `docs/adr/` for architectural decisions if it is added later. See `docs/agents/domain.md`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
