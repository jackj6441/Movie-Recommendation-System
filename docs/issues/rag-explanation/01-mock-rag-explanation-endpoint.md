# Backend tracer: mock RAG Explanation endpoint

Labels: `ready-for-agent`

## Parent

PRD: `docs/prd-rag-explanation.md`

## What to build

Build the first end-to-end RAG Explanation vertical slice using a mock provider. The new synchronous RAG Explanation Endpoint should accept the same Seed Set-oriented request shape as the deterministic explanation flow, build RAG Evidence internally from existing structured data, and return a valid Structured Explanation for the top 3 Recommendations.

This slice proves the API contract and backend orchestration without requiring an external LLM provider, vector database, frontend changes, or production-grade fallback handling.

## Acceptance criteria

- [ ] A synchronous RAG Explanation Endpoint exists and accepts Seed Set input compatible with deterministic explanation requests.
- [ ] The endpoint builds RAG Evidence internally instead of accepting precomputed evidence from the frontend.
- [ ] A mock provider returns a valid Structured Explanation with a summary and item-level explanations for the Recommendation List top 3.
- [ ] Item explanations preserve Recommendation List order.
- [ ] If fewer than 3 Recommendations exist, the response explains all available Recommendations.
- [ ] The response includes `model_version`, `rag_evidence_version`, `evidence_hash`, `prompt_version`, `request_id`, and `explanation_source`.
- [ ] The endpoint does not change Recommendation ranking or replace the deterministic explanation endpoint.
- [ ] Tests verify successful mock-provider behavior without requiring network access or provider secrets.

## Blocked by

None - can start immediately.
