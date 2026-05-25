# PRD: RAG Explanation Layer

## Problem Statement

Users can receive a Recommendation List and deterministic scoring details, but the explanation experience is still mechanical. The current explanation data exposes signals and similar movies, but it does not turn that evidence into concise, trustworthy language that helps a user understand why the top Recommendations fit their Seed Set.

The project should improve explanation quality without destabilizing ranking. RAG must explain Recommendations after ranking has already happened, not decide which Movies are recommended.

## Solution

Add a synchronous RAG Explanation Endpoint that generates a Structured Explanation from deterministic RAG Evidence. The endpoint will preserve the existing hybrid recommender flow: users submit a Seed Set, the backend computes the Deterministic Explanation, builds grounded RAG Evidence, asks an external LLM provider for a strictly validated Structured Explanation, caches successful responses, and falls back to a Deterministic Fallback when RAG is unavailable.

The first version explains the top 3 Recommendations in English only. It uses existing structured project data only and does not introduce a vector database, database persistence, streaming, RAG ranking, or natural-language movie search.

## User Stories

1. As an end user, I want a short natural-language summary of my Recommendation List, so that I can understand the overall theme of the Recommendations.
2. As an end user, I want item-level explanations for the top 3 Recommendations, so that I can understand why the strongest Recommendations were selected.
3. As an end user, I want explanations grounded in my Seed Set, so that the explanation reflects my actual inputs.
4. As an end user, I want explanations grounded in Content Signal and Hybrid Score, so that the explanation reflects the recommender's real signals.
5. As an end user, I want the app to keep working when the RAG provider fails, so that recommendations are still usable.
6. As an end user, I want the explanation tone to be concise and trustworthy, so that it feels informative rather than promotional.
7. As an end user, I want explanations to avoid unsupported movie facts, so that I am not misled by generated claims.
8. As a frontend user, I want RAG failures to degrade gracefully, so that the UI can show a basic explanation rather than an error wall.
9. As a frontend developer, I want a stable Structured Explanation schema, so that rendering logic is simple and testable.
10. As a frontend developer, I want item explanations to stay in the same order as the Recommendation List top 3, so that I can map explanations to Recommendations reliably.
11. As a frontend developer, I want `explanation_source`, so that I can distinguish generated RAG from cached RAG and deterministic fallback.
12. As a frontend developer, I want fixed fallback reason values, so that UI and tests can handle known failure states safely.
13. As a backend developer, I want the backend to construct RAG Evidence internally, so that the frontend cannot send stale or forged evidence.
14. As a backend developer, I want the RAG endpoint to reuse existing Seed Set validation, so that request semantics remain consistent with deterministic explanations.
15. As a backend developer, I want a provider interface, so that the RAG provider can be swapped without rewriting product logic.
16. As a backend developer, I want a mock provider, so that local development and CI can run without network calls or API keys.
17. As a backend developer, I want failure mock providers, so that timeout and invalid JSON fallback paths can be tested deterministically.
18. As a backend developer, I want strict JSON schema validation, so that malformed LLM output never reaches the frontend as trusted explanation data.
19. As a backend developer, I want cache keys based on model version, evidence hash, prompt version, and provider model, so that cached explanations match the evidence and prompt that produced them.
20. As a backend developer, I want RAG metadata logs, so that provider failures, latency, cache behavior, and fallback reasons can be debugged.
21. As an operator, I want RAG timeout behavior, so that slow provider calls do not degrade the core recommender experience.
22. As an operator, I want RAG provider secrets configured only on the backend, so that API keys are never exposed to browsers or committed to git.
23. As an operator, I want a separate RAG cache TTL, so that generated explanation caching can be tuned independently from deterministic explanation caching.
24. As a maintainer, I want the RAG layer not to store full explanations in a database for v1, so that the feature remains small until user value is proven.
25. As a maintainer, I want RAG not to participate in ranking, so that recommendation quality remains measurable and debuggable.
26. As a maintainer, I want natural-language movie search to remain out of v1, so that explanation quality can be validated before expanding RAG scope.

## Implementation Decisions

- Build a RAG Explanation module behind a small interface rather than adding the logic directly to the existing API endpoint module.
- Add a new synchronous endpoint for RAG Explanation. It should not replace the existing deterministic explanation endpoint.
- The request accepts the same Seed Set-oriented inputs as deterministic explanation, such as `seeds` and `shuffle`; it does not accept a full precomputed explanation payload from the frontend.
- The backend composes the flow internally: validate seeds, compute or load Deterministic Explanation, build RAG Evidence, compute evidence hash, check cache, call provider when needed, validate output, and return either generated output or Deterministic Fallback.
- RAG Evidence v1 uses existing structured project data only: Seed Set, Recommendation List, Score Contributions, movie title, movie genre metadata, Similar Movies, and Model Version.
- Do not add a vector database in v1.
- Do not store full RAG Explanations in a database in v1. Use cache plus metadata logs.
- Add an external provider implementation behind a provider interface.
- Add provider modes for mock success, invalid JSON, and timeout behavior so local development and tests can exercise success and failure paths without real provider calls.
- Provider API keys and provider configuration live only in backend environment variables. No provider key should appear in frontend code or committed files.
- The response is a Structured Explanation: summary plus item-level explanations.
- Summary covers the full Recommendation List.
- Item-level explanations cover exactly the Recommendation List top 3 when at least 3 Recommendations exist; otherwise they cover all available Recommendations.
- Item explanations must preserve Recommendation List order.
- English is the only supported output language in v1.
- The response uses `explanation_source` with v1 values `rag`, `rag_cache`, and `deterministic_fallback`.
- The response uses fixed `fallback_reason` values, including provider timeout, provider error, invalid JSON, schema validation failure, cache error, disabled, empty recommendation list, and unknown.
- The response includes `model_version`, `rag_evidence_version`, `evidence_hash`, `prompt_version`, and `request_id`.
- `rag_evidence_version` identifies the evidence schema, initially `structured-v1`.
- `evidence_hash` identifies the concrete evidence content used for one request.
- `prompt_version` is a first-class field and cache-key input, initially `rag-exp-v1`.
- RAG cache key includes model version, evidence hash, prompt version, and provider model.
- Add a separate `RAG_CACHE_TTL_SECONDS` configuration with default 3600 seconds.
- LLM provider timeout is 8 seconds, with an overall endpoint target of 10 seconds or less.
- No streaming in v1.
- No formal feedback system in v1. Include `request_id` so future feedback can be linked to a specific explanation.
- Evidence references in item explanations use a compact string enum. V1 allowed values are `seed_set`, `content_signal`, and `hybrid_score`.
- The explanation tone should be concise, trustworthy, and non-marketing.

## Testing Decisions

- Tests should focus on external behavior: request validation, response shape, fallback behavior, cache behavior, and provider boundary behavior. They should not assert private implementation details.
- Test the RAG service module as a deep module with mocked deterministic explanation input and provider implementations.
- Test schema validation by feeding valid JSON, invalid JSON, unknown evidence enum values, missing required fields, mismatched movie IDs, and item-order violations.
- Test deterministic fallback behavior for provider timeout, provider error, invalid JSON, schema validation failure, disabled provider, cache error, and empty Recommendation List.
- Test cache behavior by verifying equivalent evidence, prompt version, model version, and provider model produce cache hits, while changed evidence hash or prompt version misses cache.
- Test request validation by reusing existing Seed Set validation cases: empty seeds, too many seeds, invalid movie IDs, and unavailable content.
- Test provider modes without network calls: mock success, mock invalid JSON, and mock timeout.
- Test that provider secrets are never required for mock provider tests.
- Test that item explanations correspond to the Recommendation List top 3 and preserve order.
- Test that the endpoint returns 200 with deterministic fallback for empty Recommendation Lists and does not call the provider.
- Existing prior art is the FastAPI endpoint structure, current deterministic recommendations/explanations behavior, Redis cache usage, and environment-variable configuration.

## Out of Scope

- RAG ranking or LLM-driven recommendation selection.
- Natural-language movie search.
- Vector database, document ingestion, embedding index, or external movie corpus.
- Plot summaries, reviews, tags, or external web data as RAG Evidence.
- Multi-language output.
- Streaming response.
- Database persistence of generated explanations.
- User feedback collection endpoint.
- Admin/debug endpoint for provider details.
- Replacing the deterministic explanation endpoint.
- Changing the core hybrid recommendation algorithm.

## Further Notes

- This PRD follows the ADR decision to use RAG for explanations before ranking.
- The RAG layer is an enhancement over the existing Recommendation List and Deterministic Explanation. It must not change the Recommendations returned by the core recommender.
- The first implementation should optimize for a small, testable vertical slice rather than a broad RAG platform.
- If v1 proves useful, the likely next expansion is Natural-Language Movie Search. A vector database should only be considered after new evidence sources such as plot summaries, tags, or reviews are introduced and need retrieval.
