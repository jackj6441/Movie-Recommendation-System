# PRD: Conversational RAG Recommendation (Chat)

## Problem Statement

Users receive a strong **Recommendation List** from multi-retriever fusion (and optional LTR), but the product experience is still a rigid three-step wizard plus a separate **Structured Explanation** layer (`summary` plus three fixed item reasons). That flow does not match how people naturally describe taste, refine filters, or explore results in dialogue.

The current **RAG Explanation Endpoint** explains an already-ranked list in a fixed schema. It does not orchestrate the **Seed Set**, genre filters, or follow-up turns. Portfolio reviewers and demo users expect a ChatGPT-style entry: a central message box, quick genre chips under the input, streaming assistant text, and recommendations that update when the conversation updates context—without letting the language model change ranking.

## Solution

Replace the product-facing **RAG Explanation** with a **Conversational RAG Recommendation** experience:

1. **Chat-first UI** — Centered composer (ChatGPT-like) with up to three **Genre** chips directly below the search box.
2. **Server-side chat sessions** — Each conversation has a `session_id`; the backend stores thread history, the active **Seed Set** context, and the latest **Recommendation List**.
3. **Deterministic orchestration (v1)** — A rules-based **Context Resolver** turns user text and genre chips into `seeds`, `genres`, and optional year bounds, then calls the existing **Seed Ranker** (same behavior as `POST /recommendations`). The LLM only generates grounded natural language (streaming); it does not select or reorder **Recommendations**.
4. **SSE delivery** — Assistant prose streams as tokens; a **final** event delivers updated `context`, optional **Recommendation List**, `model_version`, and clarification flags.
5. **Hard removal of Structured Explanation product path** — Delete the **RAG Explanation Endpoint** and frontend per-item RAG reasons. Keep **Deterministic Explanation** as a debug/internal evidence source only.

Ranking remains measurable, reproducible, and unchanged in authority. RAG improves discovery and presentation, not rank.

## User Stories

### End user — discovery and dialogue

1. As an end user, I want a single chat screen to start recommending movies, so that I do not walk through a separate wizard first.
2. As an end user, I want genre quick-picks under the message box, so that I can narrow taste in one tap like ChatGPT action chips.
3. As an end user, I want to describe movies in plain language, so that the system can anchor recommendations without manually searching every title first.
4. As an end user, I want to select only genres and send a short message, so that I still receive a **Recommendation List** when I have not named a specific movie.
5. As an end user, I want a clear follow-up question when I provide neither genres nor movie hints, so that I am not shown random recommendations.
6. As an end user, I want assistant text to stream while I wait, so that the experience feels responsive.
7. As an end user, I want recommendations to appear after the assistant finishes streaming when a list is available, so that prose and results feel connected.
8. As an end user, I want to refine filters in follow-up messages (e.g., “more 90s sci-fi”), so that the **Recommendation List** updates from the same conversation.
9. As an end user, I want explanations grounded in my **Seed Set** and scores, so that I trust why movies appear.
10. As an end user, I want the assistant to avoid inventing plot, cast, or review facts, so that I am not misled by hallucinations.
11. As an end user, I want recommendations to keep working when the LLM provider fails, so that I still see ranked movies with safe fallback copy when possible.
12. As an end user, I want poster-rich recommendation cards embedded in the conversation, so that movies are recognizable at a glance.
13. As an end user, I want the product to remain English-first for generated prose in v1, so that scope stays testable.

### End user — trust and constraints

14. As an end user, I want the same movies I would get from the core ranker for the same **Seed Set** and filters, so that chat does not secretly change scores.
15. As an end user, I want up to five **Seed Movies** in a **Seed Set**, so that the product rules stay consistent with the API.
16. As an end user, I want at most three genres selected, so that filters stay interpretable.
17. As an end user, I want empty filter results handled gracefully, so that the assistant can explain no matches instead of showing a broken UI.

### Frontend developer

18. As a frontend developer, I want one chat API with `session_id`, so that I do not coordinate separate recommendation and explanation calls on the product path.
19. As a frontend developer, I want SSE events with a documented `final` payload, so that I can render streaming text and attach recommendation cards once per turn.
20. As a frontend developer, I want `needs_clarification` on the final event, so that I can show a question UI without an empty recommendation grid.
21. As a frontend developer, I want genre chip state sent on each turn, so that the backend stays aligned with the UI.
22. As a frontend developer, I want to remove wizard steps and structured RAG reason fields, so that the codebase matches the new product flow.
23. As a frontend developer, I want `model_version` on recommendation payloads, so that portfolio evidence stays accurate.

### Backend developer

24. As a backend developer, I want a **Session Store** module with TTL, so that multi-turn state is encapsulated and testable.
25. As a backend developer, I want a **Context Resolver** that does not call the LLM in v1, so that seed and filter logic stays deterministic and unit-testable.
26. As a backend developer, I want title resolution via existing case-insensitive movie search, so that catalog rules stay centralized.
27. As a backend developer, I want genre-only bootstrap via existing genre seed endpoints logic, so that cold-start behavior reuses popularity-based seeds.
28. As a backend developer, I want the **Seed Ranker** invoked once per successful turn, so that ranking logic is not duplicated.
29. As a backend developer, I want **Deterministic Explanation** built internally for **RAG Evidence**, so that the LLM prompt is grounded without exposing debug payloads to the product UI.
30. As a backend developer, I want mock provider modes for SSE and failure paths, so that CI does not require network or API keys.
31. As a backend developer, I want provider secrets only in backend environment variables, so that keys never reach the browser.
32. As a backend developer, I want chat turn metrics separate from retired explanation metrics, so that operators can monitor the new path.
33. As a backend developer, I want clarification turns to skip ranking, so that latency and cost stay low for invalid input.

### Operator and maintainer

34. As an operator, I want chat turn latency and outcome counters in Prometheus metrics, so that I can compare p95 against benchmarks.
35. As an operator, I want session TTL configurable, so that memory use stays bounded on long-running instances.
36. As a maintainer, I want the **RAG Explanation Endpoint** removed, so that we do not maintain two RAG product contracts.
37. As a maintainer, I want **Deterministic Explanation** retained for debug and evidence, so that signal inspection remains possible.
38. As a maintainer, I want an ADR note that conversational RAG supersedes explanation-only RAG for the product path, so that future work does not reintroduce structured item reasons as the primary UX.
39. As a maintainer, I want v2 LLM-assisted title extraction explicitly deferred, so that v1 ships with testable rules first.

### Portfolio and evaluation

40. As a portfolio reviewer, I want the architecture diagram to show chat orchestration over fusion/LTR ranking, so that the ML story stays coherent.
41. As a portfolio reviewer, I want benchmarks to measure the chat endpoint time-to-final, so that evidence JSON reflects the new UX.
42. As an evaluator, I want offline ranking metrics unchanged by this PRD, so that Recall/NDCG tuning remains valid.

## Implementation Decisions

### Product and architecture

- **Supersedes** the shipped **Structured Explanation** product experience and **RAG Explanation Endpoint**. The ADR “RAG for explanations before ranking” remains valid in spirit: the LLM still does not rank; conversational RAG **orchestrates** inputs to the ranker and **presents** outputs.
- **Ranking authority**: **Seed Ranker** (multi-retriever fusion, optional `RANKING_MODE=ltr`) is the only source of **Recommendation List** order and scores. The language model must not emit ranked `movie_id` lists that override the ranker.
- **v1 orchestration**: **Context Resolver** uses rules, substring movie search, and genre bootstrap—not LLM tool calls. **v2** may add LLM `extract_movie_titles` tools that still must resolve through search before entering the **Seed Set**.

### Deep modules (build or modify)

| Module | Responsibility | Interface (conceptual) |
|--------|----------------|----------------------|
| **Session Store** | Create/load sessions; append user/assistant messages; persist `context` and optional last **Recommendation List**; enforce TTL | `create_session()`, `get(session_id)`, `append_turn(...)`, `expire()` |
| **Context Resolver** | Merge genre chips + message + prior context → next `seeds`, `genres`, `year_min`, `year_max`; gate clarification; bootstrap seeds from genres | `resolve(message, genres, prior_context) → ResolveResult` where `ResolveResult` is either `ready(context)` or `clarify(reason)` |
| **Chat Orchestrator** | Single turn pipeline: resolve → rank (if ready) → build evidence → stream provider → emit final | `run_turn(session_id, message, genres) → AsyncIterator[SSEEvent]` |
| **Evidence Builder** | Produce **RAG Evidence** from **Deterministic Explanation** fields (seed movies, top recommendations, **Content Signal**, fusion/LTR final scores, **Similar Movies**) for prompts only | `build_evidence(rank_result) → EvidencePayload` |
| **Chat Provider** | Mock and external streaming; timeouts; fallback copy generation when provider fails | `stream_completion(evidence, mode) → tokens`; deterministic fallback text without changing rank output |
| **Seed Ranker** (existing) | Unchanged ranking core | Called with resolved **Seed Set** and filters |
| **Chat Metrics** (existing metrics module extended) | Per-turn outcomes: success, clarification, provider_timeout, rank_error, sse_abort | `record_chat_turn(outcome, reason?)` |

Check with implementer: all of **Session Store**, **Context Resolver**, and **Chat Orchestrator** should have isolated unit tests. **Chat Provider** tested via mock modes only in CI. **Evidence Builder** tested as pure functions on fixture rank outputs.

### Clarification and seed rules

- **Clarification gate**: If the user sends zero genres (from chips) and the resolver extracts zero movie titles from the message and the session has no existing **Seed Movies**, return `needs_clarification: true` with no **Recommendation List** and no ranker call.
- **Seed merge**: `resolved_seeds = (session seeds ∪ search-resolved ids ∪ genre-bootstrap ids)`, deduplicated, capped at five.
- **Genre bootstrap**: When genres are selected but seeds are insufficient, populate **Seed Set** from per-genre popular seed movies (same semantics as current genre seed API), until at least one valid seed exists.
- **Title resolution (v1)**: For each extracted candidate string, query movie search; accept top match only above a configurable similarity threshold (exact/substring policy documented in resolver).
- **Year filters (v1)**: Simple regex patterns on message (e.g., decades, “after YEAR”) merge into context; genre chips remain source of truth for **Genre** filters.

### API contract

- **New**: `POST /rag/chat` — accepts `session_id` (optional), `message`, `genres` (0–3). Creates session when absent. Returns `text/event-stream`.
- **SSE events**:
  - `token`: `{ "delta": string }`
  - `final`: `{ session_id, turn_id, needs_clarification, context, recommendations | null, assistant_message, explanation_source, model_version, ranking_mode?, clarification_reason?, rank_error?, chat_fallback_reason? }`
- **Delete**: **RAG Explanation Endpoint** (`POST /rag/explanations`) and all **Structured Explanation** response fields from the product contract.
- **Retain**: `POST /recommendations` (direct rank, tests, evidence tooling); `POST /explanations` (**Deterministic Explanation**, debug); `GET /movies/search`; `GET /genres`; genre seed reads.
- **Session storage**: In-process map with `RAG_SESSION_TTL_SECONDS` (default 3600). Document single-instance limitation; Redis session store is out of scope for v1.

### Provider and fallback

- Reuse provider environment pattern (`RAG_PROVIDER`, external API key, model name, timeout ~8s).
- Mock modes: normal stream, slow stream, forced clarification path, provider timeout, rank failure, disabled provider.
- On provider failure after a successful rank: return **Recommendation List** in `final` with `explanation_source: deterministic_fallback` and safe generic assistant text (no **Structured Explanation** schema).
- `RAG_CHAT_VERSION` (or equivalent) identifies prompt/schema generation for logging and portfolio evidence—not the retired `structured-v1` evidence schema exposed to clients.

### Frontend

- Replace wizard (genres step → seeds step → results) with **Chat Home** (composer + genre chips) and **Chat Thread** (messages + embedded recommendation cards on `final`).
- Remove calls to **RAG Explanation Endpoint** and per-hero structured `reason` / `evidence` UI.
- Parse SSE client-side; on `final`, render recommendation cards (reuse existing results presentation components without RAG item fields).
- Persist `session_id` in client state (optional `sessionStorage` for refresh behavior is acceptable v1).
- Keep **Evidence** dashboard tab; update copy and benchmark fields from “RAG explanations” to “RAG chat”.

### Observability and portfolio

- Rename Prometheus counters from RAG explanation sources to **chat turn outcomes**.
- Update API benchmark harness to measure time-to-`final` for `POST /rag/chat` and sync portfolio evidence accordingly.

### Schema shape (final event, decision-rich)

```json
{
  "session_id": "uuid",
  "turn_id": "uuid",
  "needs_clarification": false,
  "context": {
    "seeds": [{ "movie_id": 1, "title": "Toy Story (1995)" }],
    "genres": ["Comedy"],
    "year_min": null,
    "year_max": null
  },
  "recommendations": {
    "items": [],
    "seed_movies": [],
    "model_version": "dev",
    "ranking_mode": "multi_retriever_fusion"
  },
  "assistant_message": "…",
  "explanation_source": "rag"
}
```

## Testing Decisions

### What makes a good test

- Assert **external behavior** only: HTTP status, SSE event sequence, `final` JSON shape, session continuity, and side effects on metrics—not private resolver helpers or prompt strings.
- Do not assert LLM prose wording; assert presence of `assistant_message`, streaming token count in mocks, and fallback flags.
- Ranking assertions: when `needs_clarification` is false and seeds resolve, `final.recommendations.items` movie IDs and order must match a direct **Seed Ranker** call with the same context (golden comparison).

### Modules to test

| Module | Test focus |
|--------|------------|
| **Context Resolver** | Clarification gate; genre-only bootstrap; title search merge; cap at five seeds; year regex; merge with session prior context |
| **Session Store** | Create/get; TTL expiry; message append; context update |
| **Chat Orchestrator** | End-to-end turn with mock provider: clarify path skips rank; happy path emits tokens + final with recommendations |
| **Chat Provider** | Mock SSE chunking; timeout → fallback flag |
| **API integration** | `POST /rag/chat` SSE; deleted explanation endpoint returns 404; `/explanations` still works |
| **Frontend** | Chat send → mock stream → cards render; clarification UI; no `/rag/explanations` fetch |

### Prior art

- Existing FastAPI tests for seed validation and `POST /recommendations` / `POST /explanations`.
- Retired `test_rag_explanations` patterns for provider mock env vars—migrate to chat turn tests.
- `App.test.tsx` RAG explanation suite—rewrite for chat flow.
- `conftest.py` observability reset fixture for metrics isolation.

### Explicitly not required in v1

- Snapshot tests of LLM paragraphs.
- Multi-instance session stickiness tests.
- Load tests beyond existing benchmark CLI.

## Out of Scope

- **RAG ranking** or LLM-chosen **Recommendation List** order.
- **Vector database**, plot/review ingestion, or web retrieval beyond existing catalog search and ranker signals.
- **LLM tool calling** for context updates in v1 (deferred to v2).
- **Redis** or database-backed session persistence.
- **Multi-language** generated prose beyond English v1 prompts.
- **User accounts** / `user_id` in the product UI.
- **Replacing** `POST /explanations` or `POST /recommendations` for debug and evaluation.
- **RAG refactor** of portfolio Evidence dashboard beyond metric label updates.
- **Natural-language movie search** as a standalone feature (partial overlap with resolver search is in scope only for seed resolution).
- **Streaming partial recommendation cards** before rank completes (only text streams; list appears in `final`).
- **Formal user feedback** endpoint linked to turns (optional `turn_id` is in scope for future use only).

## Further Notes

- Update domain glossary: introduce **Conversational RAG Recommendation** / **RAG Chat Turn**; deprecate **Structured Explanation** and **RAG Explanation Endpoint** for product use. **Hybrid Score** language should align with **fusion_score** / multi-retriever signals in evidence shown to the model.
- Supersede `docs/prd-rag-explanation.md` for product planning; keep it in repo history for reference until archived.
- Implementation milestones suggested: (1) Session Store + Context Resolver tests, (2) SSE chat endpoint + delete explanation endpoint, (3) frontend ChatGPT layout, (4) benchmarks and docs.
- Single-instance Docker Compose remains the primary deployment story; document session stickiness if horizontally scaled later.
