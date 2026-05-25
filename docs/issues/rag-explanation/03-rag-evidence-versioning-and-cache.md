# RAG Evidence versioning and cache

Labels: `ready-for-agent`

## Parent

PRD: `docs/prd-rag-explanation.md`

## What to build

Add versioning, hashing, caching, and metadata logging for RAG Explanations. Cached explanations must be tied to the exact RAG Evidence, prompt version, model version, and provider model that produced them, so stale or mismatched generated explanations are not reused.

This slice makes RAG Explanation cheaper, more stable, and easier to debug without adding database persistence.

## Acceptance criteria

- [ ] RAG Evidence has a schema version, initially `structured-v1`.
- [ ] A stable `evidence_hash` is computed from canonicalized RAG Evidence content.
- [ ] `prompt_version` is a first-class response and cache-key field, initially `rag-exp-v1`.
- [ ] RAG cache keys include model version, evidence hash, prompt version, and provider model.
- [ ] Cache hits return `explanation_source: \"rag_cache\"`.
- [ ] Cache misses that generate valid output return `explanation_source: \"rag\"`.
- [ ] `RAG_CACHE_TTL_SECONDS` is configurable with default 3600 seconds.
- [ ] Metadata logs include request id, versions, evidence hash, provider mode/model, latency, cache hit/miss, validation result, fallback reason, and error type.
- [ ] Full prompts, full provider responses, API keys, and sensitive user data are not logged by default.
- [ ] Tests verify cache hit/miss behavior and version/hash cache invalidation.

## Blocked by

- Strict schema validation and Deterministic Fallback.
