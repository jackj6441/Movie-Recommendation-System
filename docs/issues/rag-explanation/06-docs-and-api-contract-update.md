# Docs and API contract update

Labels: `ready-for-agent`

## Parent

PRD: `docs/prd-rag-explanation.md`

## What to build

Update project documentation to describe the completed RAG Explanation v1 behavior. The docs should make the API contract, environment variables, provider modes, fallback semantics, cache/version fields, and out-of-scope boundaries clear for future developers and agents.

This slice closes the implementation loop by aligning docs with the final behavior.

## Acceptance criteria

- [ ] API docs describe the RAG Explanation request and response schema.
- [ ] API docs list `explanation_source`, `fallback_reason`, evidence enum values, version fields, and `request_id`.
- [ ] API docs document empty Recommendation List behavior.
- [ ] Development docs list RAG provider environment variables and mock provider modes.
- [ ] Documentation states that RAG Explanation does not participate in Recommendation ranking.
- [ ] Documentation states that v1 is English-only, non-streaming, top-3 item explanations, and structured-data-only.
- [ ] Documentation includes cache TTL and timeout configuration.
- [ ] Documentation does not include real provider secrets.
- [ ] PRD-adjacent docs remain consistent with `CONTEXT.md` and ADR-0001.

## Blocked by

- Backend tracer: mock RAG Explanation endpoint.
- Strict schema validation and Deterministic Fallback.
- RAG Evidence versioning and cache.
- External provider integration behind provider interface.
- Frontend display for RAG Explanation.
