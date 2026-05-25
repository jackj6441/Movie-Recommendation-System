# Domain Docs

How engineering skills should consume this repo's domain documentation when exploring the codebase.

## Layout

This is currently a single-context repo for an AI-powered movie recommendation system.

Read these files first when they are relevant:

- `README.md`: repo structure, local startup, and API quickstart.
- `RULES.md`: fixed stack, change principles, security, and runtime requirements.
- `docs/prd.md`: product goals, non-goals, metrics, and risks.
- `docs/architecture.md`: system components and data flow.
- `docs/api.md`: API contract and examples.
- `CONTEXT.md`: domain glossary if it is added later.
- `docs/adr/`: architectural decisions if this directory is added later.

If `CONTEXT.md` or `docs/adr/` do not exist, proceed silently. Do not suggest creating them upfront unless the user asks for domain modeling or architectural decision capture.

## Domain vocabulary

Prefer the existing project language:

- Seed movies: 1-5 movies selected by the user to anchor recommendations.
- Genres: optional user-selected filters, currently 0-3 selections.
- Recommendations: top-k movie results returned by `POST /recommendations`.
- Explanations: score and similarity details returned by `POST /explanations`.
- NCF: neural collaborative filtering model exported to ONNX.
- Content embeddings: movie title and genre embeddings used for seed-based similarity.
- Hybrid ranking: fusion of NCF and content signals, controlled by `ALPHA`.
- Model version: response field used to identify model-backed outputs and cache keys.

## ADR conflicts

If your output contradicts a future ADR, surface it explicitly rather than silently overriding it.
