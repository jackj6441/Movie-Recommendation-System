# Strict schema validation and Deterministic Fallback

Labels: `ready-for-agent`

## Parent

PRD: `docs/prd-rag-explanation.md`

## What to build

Harden RAG Explanation output handling so malformed, unsupported, or unavailable generated explanations never break the user experience. The system should strictly validate Structured Explanation output, accept only known evidence references and source/fallback enums, and return a Deterministic Fallback when generated output cannot be trusted.

This slice turns the mock tracer into a reliable product path by making failure behavior explicit and testable.

## Acceptance criteria

- [ ] Structured Explanation validation rejects invalid JSON, missing required fields, unknown evidence values, mismatched `movie_id` values, and item-order violations.
- [ ] V1 evidence references are limited to `seed_set`, `content_signal`, and `hybrid_score`.
- [ ] V1 `explanation_source` values are limited to `rag`, `rag_cache`, and `deterministic_fallback`.
- [ ] V1 `fallback_reason` values are fixed and include provider timeout, provider error, invalid JSON, schema validation failure, cache error, disabled, empty Recommendation List, and unknown.
- [ ] Mock failure provider modes exist for invalid JSON and timeout behavior.
- [ ] Provider timeout, provider error, invalid JSON, and schema validation failure return Deterministic Fallback instead of crashing the endpoint.
- [ ] Empty Recommendation Lists return a successful empty Structured Explanation without calling a provider.
- [ ] Tests cover all validation and fallback paths through public service or endpoint behavior.

## Blocked by

- Backend tracer: mock RAG Explanation endpoint.
