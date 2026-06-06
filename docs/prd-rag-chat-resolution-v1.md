# PRD: Conversational RAG — Context Resolution & Multi-Turn UX (v1.1 → v1.3)

Supersedes gaps in the shipped chat MVP (issue #15). Ranking authority stays on **Seed Ranker** / fusion; LLM prose remains optional (`RAG_PROVIDER=mock` default). This PRD covers **deterministic Context Resolver** upgrades and **stateful chat product** interactions.

## Problem Statement

The conversational recommendation path is live, but users hit three core failures: **genre-only turns never reach the API** (frontend blocks empty messages), **bare movie titles** (e.g. `Toy Story` without quotes) are not resolved, and **`no_resolvable_seeds`** ends in text-only clarify with no recovery path.

Beyond those bugs, the experience lacks **visible recommendation context** (**Seed Set**, genres, year filters). Multi-turn use becomes opaque: users cannot see what the system remembered, cannot reset taste, and may confuse **disambiguation candidates** with **Recommendations**. Without explicit **session update rules**, **seed merge semantics**, and **SSE contracts**, implementations will pass tests yet feel broken in dialogue.

**v1.2 polish (post-ship feedback):** **Current taste** scrolls out of view during long threads; disambiguation is text-heavy despite poster-forward brand; chat returns up to 24 **Recommendations** (too many); **More like this** does not scroll to new results; removing the last seed/genre chip appears broken when the resolver receives an empty **Seed Set**.

**v1.3 (grill-me, Jun 2026):** Users see bootstrap seeds in **Current taste** after genre-only sends (confused with picks); recommendations skew pre-2005; genre chips disappear after turn one; scroll-to-reply is flaky; no multi-chat history without login. Visual polish (B+C) is **out of scope** for this PRD slice — tracked under `/impeccable` separately. **Mobile adapt is deferred** for v1.3.

## Solution

Deliver a v1.1 chat resolution and interaction layer:

1. **Resolver v1** — Whole-message catalog search; explicit `seed_movie_ids` (highest priority); genre bootstrap; `seed_update_mode` (`append` | `replace`); disambiguation with up to 10 rich candidates when seeds cannot be resolved; partial invalid seed handling via `warnings`.
2. **Session semantics** — Documented per-outcome updates to genres, years, and **Seed Set**; reset taste without full page reload.
3. **Chat UI** — Genre-only send; human-readable user turns for empty messages; **Context Chips** for current taste; **Start over**; **Disambiguation Picker** (not labeled as recommendations); optional **More like this** on recommendation cards; loading/disabled rules for SSE.
4. **SSE final schema** — `needs_disambiguation`, `disambiguation_candidates`, `warnings`, optional `debug` (non-prod), empty **Recommendation List** fallback; token-optional turns.
5. **Observability** — Outcome- and resolve-reason metrics for portfolio evidence.

OpenAI / external provider wiring remains **out of scope** for this PRD (deterministic assistant copy only).

## User Stories

### End user — core fixes

1. As an end user, I want to send a turn with only genre chips and an empty message, so that I receive a **Recommendation List** without typing filler text.
2. As an end user, I want to type a movie title without quotes (any common casing), so that the system anchors my **Seed Set** via catalog search.
3. As an end user, when the system cannot resolve my input to seeds, I want up to ten movies to pick from, so that I can still start recommendations.
4. As an end user, I want copy that explains these ten movies are **not** final recommendations, so that I am not confused about system intent.
5. As an end user, I want to select one to five movies from that list, so that my choices become **Seed Movies** for the next rank.
6. As an end user, I want year and genre shown on disambiguation rows, so that I can tell apart remakes and same-title films.
7. As an end user, I want to see my current genres, **Seed Movies**, and year filters at all times, so that multi-turn chat stays understandable.
8. As an end user, I want to remove a genre or seed chip, so that I can correct mistakes without starting a new browser session.
9. As an end user, I want a **Start over** control, so that I can clear taste and begin a new direction.
10. As an end user, when I pick a disambiguation movie, I want that choice to become my anchor without silently keeping unrelated old seeds, so that recommendations match my latest intent.
11. As an end user, I want empty chat messages to appear as clear summary lines (not debug placeholders), so that the thread reads naturally.
12. As an end user, I want to send another turn when I already have seeds but no new text (e.g. refresh recommendations), so that follow-up ranking works.
13. As an end user, when filters yield no **Recommendations**, I want `empty_recommendations` clarification with guidance while keeping my **Seed Set**, so that I can remove filters and try again.
14. As an end user, I want the assistant to still respond when a turn has only a `final` event and no tokens, so that disambiguation does not look stuck loading.
15. As an end user, I want send disabled while a turn is in flight, so that I do not duplicate requests.

### End user — multi-turn refinement (v1.1 required)

16. As an end user, I want to tap **More like this** on a **Recommendation** card, so that that **Movie** is appended to my **Seed Set** and I get a new **Recommendation List** in the same session.
17. As an end user, when I pass unknown genre labels, I want a helpful message pointing to supported genres, so that I know the chip was not recognized.
18. As an end user, I want at most five **Seed Movies** with a visible limit message if I try a sixth, so that rules match the API.

### End user — v1.2 UX polish (required)

19. As an end user, I want **Current taste** pinned in a right-side sticky rail while I scroll the chat, so that I always know what the system remembers.
20. As an end user, on a phone I want taste collapsed into a compact strip (not a blocking rail), so that the composer stays usable.
21. As an end user, I want disambiguation picks shown as **poster cards** (not a text-only list), so that I can recognize movies at a glance.
22. As an end user, I want at most ten **Recommendations** per chat turn (one hero + up to nine more), so that the page does not feel overwhelming.
23. As an end user, after **More like this** I want the view to scroll to the newest assistant reply, so that I see the updated list without hunting.
24. As an end user, when I remove the last **Seed Movie** but still have genres, I want new recommendations from genres only, so that × always works.
25. As an end user, when I remove the last seed and last genre (and year), I want taste cleared like **Start over**, so that I am not stuck in a broken state.

### End user — v1.3 (required)

26. As an end user, when I send genre-only, I want **Current taste** to show only what I chose (genres, typed titles, disambiguation picks, **More like this**), not internal bootstrap movies.
27. As an end user, when I have not set a year, I want recommendations biased to **2005+**, with **Include older movies** to relax the filter.
28. As an end user, I want to add or remove genres after the first turn via the **taste rail** (+ genre chips) and a collapsible **Edit genres** in the composer.
29. As an end user, I want a **desktop** left sidebar with **New chat**, multiple local sessions (switch / delete), and turn links that scroll the thread — no account login.
30. As an end user, I want scroll-to-reply to work after every assistant turn, **More like this**, disambiguation submit, and sidebar turn navigation (with retry, not silent failure).

### Frontend developer

19. As a frontend developer, I want `seed_movie_ids` and `seed_update_mode` on chat requests, so that picker and card actions are explicit.
20. As a frontend developer, I want `needs_disambiguation` and `disambiguation_candidates` on the final SSE payload, so that I render pickers separately from `recommendations`.
21. As a frontend developer, I want `warnings` on the final payload, so that partial invalid ids do not fail the whole turn.
22. As a frontend developer, I want documented user-turn formatting for empty `message`, so that rendering is consistent across flows.
23. As a frontend developer, I want `canSend` to consider persisted context seeds, not only the composer, so that refresh-style turns work.
24. As a frontend developer, I want `debug` on final events when debug mode is enabled server-side, so that I can trace resolve paths without reading server logs in local development.
25. As a frontend developer, I want reset via `reset_context: true` on the same chat POST, so that session clearing does not require a second endpoint.

### Backend developer

26. As a backend developer, I want explicit seed ids to short-circuit to **Ready** without re-disambiguating, so that picker follow-ups never loop.
27. As a backend developer, I want resolve outcome types: **Ready**, **Clarify**, **Disambiguate**, so that chat orchestration stays testable.
28. As a backend developer, I want disambiguation candidate lists to include title, year, genres, poster URLs, and optional match score, so that the UI can disambiguate reliably.
29. As a backend developer, I want candidate sourcing: search hits from message, else genre-popular, else global popular, so that lists are never empty when disambiguating.
30. As a backend developer, I want invalid `seed_movie_ids` ignored with warnings, and all-invalid to fall through to disambiguate/clarify, so that chat stays resilient.
31. As a backend developer, I want session context update rules per branch documented and enforced, so that multi-turn bugs are preventable.
32. As a backend developer, I want metrics for outcomes (`ready`, `clarify`, `disambiguation`, `error`) and resolve reasons, so that operators can monitor clarification rate.
33. As a backend developer, I want SSE `event: error` for hard failures, so that the client can exit loading state.

### Operator / portfolio

34. As an operator, I want disambiguation and clarification rates in metrics, so that I can tune resolver rules.
35. As a portfolio reviewer, I want evidence that chat is a **stateful recommender** (context chips, reset, disambiguation), not a generic chatbot wrapper around rank.

## Implementation Decisions

### Deep modules (build or extend)

| Module | Responsibility | Interface (stable) |
|--------|----------------|-------------------|
| **Context Resolver** | Merge chips, message, session, explicit seeds; search; bootstrap; disambiguate | `resolve_context(...) -> Ready \| Clarify \| Disambiguate` |
| **Disambiguation Builder** | Build ≤10 candidate rows with metadata | `build_candidates(context, message, services) -> list[CandidateMovie]` |
| **Chat Turn Orchestrator** | SSE tokens + final; session updates; rank; warnings | `run_chat_turn_sse(...)` |
| **Session Store** | TTL sessions; context; reset | `create`, `get`, `save`, `reset` |
| **Catalog Services** | Search, genre seeds, titles, posters, popularity | Existing hooks + enrich candidate payload |

### Resolver priority (locked from design review)

1. Validate and merge `seed_movie_ids` (1–5, dedupe) with `seed_update_mode`: **`replace`** replaces session seeds; **`append`** merges and caps at five. **Explicit seeds always win** — if any valid ids remain after validation, outcome is **Ready** (no disambiguation), even when `message` is empty.
2. Quoted titles and `like …` patterns (existing).
3. Whole trimmed `message` (plus quoted / like-title fragments) as catalog search queries (case-insensitive substring rules unchanged). If **≥1** hit and no explicit `seed_movie_ids` are sent, return **`ambiguous_message` disambiguation** (genre pill when message maps to a catalog genre + up to 10 search-hit movie candidates; no silent first-hit seed). If **0** hits, continue to bootstrap/clarify/`no_resolvable_seeds` disambiguate paths below.
4. Genre bootstrap when seeds still empty and genres present.
5. **Clarify** `missing_genre_and_title` when no genres (after normalize), no message signal, no prior seeds, no valid explicit seeds.
6. **Clarify** `invalid_genre` when raw `genres` is non-empty but normalized genres are empty — assistant lists supported genres (catalog-aligned); **no** disambiguation candidates.
7. **Disambiguate** `no_resolvable_seeds` — return ≤10 candidates + assistant guidance; do **not** rank.

### Session context update matrix

| Outcome | Persist genres/year from request | Persist **Seed Set** | Invoke **Seed Ranker** |
|---------|----------------------------------|----------------------|-------------------------|
| **Ready** | Yes | Yes (resolved set) | Yes |
| **Disambiguate** | Yes | No (unconfirmed) | No |
| **Clarify** missing input | Only if chips explicitly sent | No | No |
| **Clarify** `empty_recommendations` | Yes (keep context) | Yes | Yes (rank ran; zero items) |
| **Reset** | Clear | Clear | No |

### Locked design decisions (grill-me)

| Topic | Decision |
|-------|----------|
| Reset taste | **A** — `reset_context: true` on `POST /rag/chat` only; no `/rag/chat/reset` in v1.1 |
| Context chip remove | **A** — each × immediately sends a chat turn (`message: ""`) with updated `genres` / `seed_movie_ids` and `seed_update_mode: replace`; UI refreshes from `final.context` |
| More like this (card) | **A** — v1.1 required; `seed_movie_ids: [id]`, `seed_update_mode: append`, `message: ""`; user turn: `More like: {title}` |
| `debug` on final SSE | **A** — include only when `RAG_CHAT_DEBUG=true` or non-production app env; omitted on public demo by default |
| Unknown genre chips | **A** — `clarification_reason: invalid_genre`; no disambiguation list; assistant points to supported genres |
| Empty **Recommendation List** after rank | **A** — `clarification_reason: empty_recommendations`, `needs_clarification: true`, empty items, session context retained; assistant suggests relaxing filters |
| Year filter chip | **A** — one chip (`Year: 2000+` or range); × sends chat with `clear_year_bounds: true` (or explicit null bounds), `message: ""`, immediate re-rank if Ready |
| Message search hits | **C** — if search returns ≥1 hit (whole message or quoted fragment), always disambiguate (`ambiguous_message`); genre pill + search-only movie grid; genre pick merges `pending_genres` + session + chips; **0 hits** → `no_resolvable_seeds` disambiguation (up to 10 candidates, may pad from genre/global popular) |

### Locked design decisions — v1.2 UX polish (grill-me)

| Topic | Decision |
|-------|----------|
| **Current taste** placement | **A** — desktop **sticky rail** on the right (“idea bubble” card); **not** in the scrolling thread. Mobile: **collapsible strip** (top or above composer), not a fixed right rail. |
| Disambiguation UI | **C** — **poster-forward**: desktop **grid** (up to 10); viewport `<768px` **horizontal scroll** snap row. Reuse `PosterTile` / thumb URLs from `disambiguation_candidates`. Not a text-only checkbox list. |
| Chat **Recommendation** cap | **A + C** — only `POST /rag/chat` caps at **10** `items` (debug `/recommendations` may stay at existing TOP_K). UI: **#1 hero** + **up to 9** in “More movies” grid (10 movies total). |
| **More like this** scroll | **A** — after turn completes, `scrollIntoView` on the **latest assistant** bubble (prose + recommendation block). |
| Remove last taste chip | **A + C** — remove last **seed** while genres remain → immediate **genre-only** re-rank (`message: ""`, no `seed_movie_ids`, genres unchanged). Remove last **genre** and no seeds/year left → **`reset_context`** (same as Start over) + empty rail / home clarify. Never leave UI with a chip that cannot × off. |

### Locked design decisions — v1.3 (grill-me)

| Topic | Decision |
|-------|----------|
| **Current taste** visible seeds | **A** — API `context.seeds` = **explicit** user seeds only (chips, search, picker, **More like this**). Genre-bootstrap / ranking seeds stay internal (`ranking_seed_ids`); never rendered in taste rail. |
| Genre editing after turn 1 | **A + C** — primary: taste rail (×, **+ Add genre**). Secondary: composer **Edit genres** `<details>` (collapsed by default); when closed, chat POST sends `genres: []` and relies on session. |
| Recency default | **D, 2005+** — when no `year_min`/`year_max`, no explicit seeds, and `recency_opt_out` is false → apply `year_min = 2005` for rank + bootstrap pool. **Include older movies** → `clear_year_bounds: true` + `recency_opt_out: true` on session. Explicit movie seeds skip the default (e.g. *Toy Story* 1995). |
| Multi-chat history | **B** — localStorage sessions: **New chat**, list, switch, delete; each holds `apiSessionId`, turns, title from first user line. No auth. Desktop sidebar; mobile deferred. |
| Scroll reliability | **B** — scroll after: assistant complete, **More like this**, disambiguation submit, sidebar turn click; `scrollToChatTarget` with rAF + timed retry. |
| Visual / motion (B+C) | **Separate `/impeccable` iteration** — three-column layout, tokens, rail motion; not blocking v1.3 functional PR. |
| Mobile | **Deferred** in v1.3 (no new adapt pass). |

### API contract (chat turn request)

```json
{
  "session_id": "optional",
  "message": "",
  "genres": ["Comedy"],
  "seed_movie_ids": [1, 2],
  "seed_update_mode": "append",
  "reset_context": false,
  "clear_year_bounds": false,
  "shuffle": false
}
```

- `clear_year_bounds: true` clears `year_min` and `year_max` on the session before resolve (used by Year chip ×).

- `message` optional when genres, explicit seeds, or session already has seeds.
- `seed_update_mode`: `"append"` (default) | `"replace"`. UI: disambiguation picker submit uses **`replace`**; **More like this** uses **`append`**.
- **`reset_context: true`** (locked): on the same `POST /rag/chat`, clears session **Seed Set**, genres, and year bounds **before** resolve on that turn. **Start over** sends one request with `reset_context: true` and `message: ""` (optional new genre chips in the same body). No separate reset endpoint in v1.1.

### API contract (SSE)

- `event: token` — `data: {"delta": string}` (optional; disambiguation may skip tokens).
- `event: final` — includes: `session_id`, `turn_id`, `context`, `needs_clarification`, `needs_disambiguation`, `clarification_reason`, `disambiguation_candidates`, `recommendations`, `assistant_message`, `warnings[]`, `model_version`, `explanation_source`.
- `context` (v1.3): `seeds` (explicit only), `genres`, `year_min`, `year_max`, `recency_opt_out` (boolean; true after **Include older movies**).
- `debug` (optional): present only when `RAG_CHAT_DEBUG=true` or deployment is non-production. Shape example: `{ "resolve_outcome", "seed_source", "normalized_genres", "candidate_count", "ranking_mode" }`. Production EC2 demo omits this field.
- `event: error` — `data: {"code", "message"}` for non-recoverable turn failures.

### Candidate row shape

```ts
type DisambiguationCandidate = {
  movie_id: number
  title: string
  year?: number
  genres?: string[]
  poster_url?: string
  poster_thumb_url?: string
  match_score?: number
}
```

### User turn display (empty `message`)

| Input | Displayed user line |
|-------|---------------------|
| Genres only | `You selected: Comedy, Sci-Fi` |
| Explicit seeds only | `You picked: Toy Story (1995), …` |
| Both | `You picked Toy Story (1995) with Comedy.` |
| Reset / refresh with session seeds | `Show more recommendations.` or `Refresh recommendations.` |

Never show debug strings like `(genre only)`.

### Disambiguation copy (assistant)

English v1 example: *"I couldn't lock onto a starting movie yet. These aren't your final recommendations—they're possible matches. Pick 1–5 to use as your Seed Set."*

### Warnings

```json
{ "code": "invalid_seed_movie_id", "movie_id": 999999999 }
```

Ignore invalid ids; proceed with valid; all invalid → disambiguate or clarify.

### Frontend components

- **Taste rail (`TasteRail`)** — replaces in-thread **Context Chips** on desktop: `position: sticky` right column inside `chat-layout` (widened grid: main thread + rail). Label **Current taste**; chips with ×. Mobile: `TasteRailCompact` collapsible above composer.
- **Taste rail** — **explicit** seeds and genres only; **+ Add genre** quick chips; **Include older movies** when year filter active; **× removes immediately** per v1.1 rules plus **last-chip** behavior (v1.2 table).
- **Edit genres** — composer `<details>`; opens `GenreChipsRow` with `aria-label` *Edit genres for this chat*; does not duplicate the first-message genre row label.
- **Chat session sidebar (`ChatSessionSidebar`)** — desktop left column; `localStorage` via `chatSessionStore`; **New chat** / switch / delete; **This thread** user-turn jump list.
- **Disambiguation Picker** — poster grid / mobile scroller; multi-select ≤5; submit with `seed_update_mode: replace`. Copy: not “Recommended movies”.
- **Start over** — sets `reset_context` or calls reset endpoint; clears local chips state.
- **Recommendation card action** — **More like this** (required v1.1) → immediate chat turn: `seed_movie_ids: [clicked_id]`, `seed_update_mode: append`, `message: ""`; cap enforced at 5 with UI toast if at limit; on success scroll to latest assistant bubble (v1.2).

### Backend (v1.2)

- **`CHAT_TOP_K = 10`** — slice ranker output in `rag_chat` only before `recommendations_payload` (do not change global `TOP_K` for `/recommendations` unless product later chooses B).
- **Resolver** — allow `seed_movie_ids: []` with `seed_update_mode: replace` to clear seeds when genres present (genre bootstrap); when context would be empty after chip remove, return `missing_genre_and_title` or honor client `reset_context`.

### Backend (v1.3)

- **`ChatContext.explicit_seed_ids`** — persisted user-visible seeds; **`ResolveReady.ranking_seed_ids`** — explicit + parsed + bootstrap for `seed_ranker.rank`.
- **`DEFAULT_RECENCY_YEAR_MIN = 2005`** — `apply_recency_default()`; skipped when explicit seeds present or `recency_opt_out`.
- **`genre_seed_ids(..., year_min=)`** — filter genre pool by year before popularity sort (bootstrap must not return only pre-2005 head).
- **`clear_year_bounds`** — clears years and sets `recency_opt_out: true`.

### Metrics (extend existing chat metrics)

- Turn outcomes: `ready`, `clarify`, `disambiguation`, `fallback`, `error`
- Resolve reasons: `explicit_seed`, `quoted_title`, `whole_message_search`, `genre_bootstrap`, `genre_disambiguation_pick`, `no_resolvable_seeds`, `ambiguous_message`, `missing_genre_and_title`, `invalid_genre`, `empty_recommendations`
- Histogram or gauge: `disambiguation_candidate_count`

## Testing Decisions

**Principle:** Assert HTTP/SSE **external behavior** and final JSON — not private resolver call order.

| Module | Tests | Prior art |
|--------|-------|-----------|
| **Context Resolver** | Toy Story bare message; genre-only bootstrap; explicit seed short-circuit; replace vs append; all/partial invalid seeds; disambiguate candidate cap; invalid genre message | `test_rag_resolve.py` |
| **Chat Turn Orchestrator** | SSE final-only disambiguation; warnings; empty recommendations; reset_context; session reuse empty message | `test_rag_chat.py` |
| **Frontend** | canSend rules; user turn strings; picker limit 5; genre-only send; taste rail sticky (layout); poster disambiguation; scroll after more-like; remove last seed/genre; explicit-only taste seeds; session sidebar; scroll retry | `App.test.tsx`, chat mocks, `chatSessionStore.test.ts` |
| **Context Resolver (v1.3)** | genre-only → empty explicit seeds, non-empty ranking seeds; default 2005+; recency opt-out; explicit seed skips year default | `test_rag_resolve.py`, `test_rag_chat.py` |

## Out of Scope

- OpenAI / `RAG_PROVIDER=external` streaming implementation
- v2 LLM title extraction tools
- **Negative feedback** / downrank (`negative_movie_ids`) — document v2 only
- Redis session store
- Shuffle via natural language keywords
- Full **Not my vibe** behavior (UI stub optional, no rank effect)

## Further Notes

- Implements grill-me decisions: deterministic prose (C), whole-message search (A), empty message + genres (A), disambiguate on `no_resolvable_seeds` (C), explicit `seed_movie_ids` multi-select (A+D).
- **v1.2** adds: taste sticky rail (A), poster disambiguation (C), chat top-10 (A+C), more-like scroll (A), last-chip remove (A+C).
- **v1.3** adds: explicit vs ranking seeds (A), 2005+ default + Include older (D), genre rail + Edit genres (A+C), multi-session sidebar (B), scroll retry (B). **Impeccable B+C** (layout / animate / tokens) is a follow-on PR, not v1.3 functional.
- Minimum v1.1 bundle if scope must shrink: Context Chips, Start over, rich candidates, `seed_update_mode`, SSE schema, user-turn rules, empty-list fallback, session-seed refresh test.
- **v1.2 delivery order:** (1) backend `CHAT_TOP_K` + empty-seed replace fix + tests, (2) `TasteRail` layout + last-chip logic, (3) poster `DisambiguationPicker` + scroll hook, (4) visual polish per DESIGN.md + smoke.
- **v1.3 delivery order (shipped):** (1) backend explicit/ranking split + 2005+ + tests, (2) taste rail semantics + Edit genres + Include older, (3) `chatSessionStore` + sidebar + scroll retry, (4) PRD/docs. Next: **`/impeccable layout` + `animate`** for B+C visual pass (desktop).

## v1.2 — Visual direction (product register)

Physical scene: user on a laptop at home, long chat thread, glancing right to confirm “what the system thinks I like” without scrolling back up. Rail: warm white surface, soft border, small caps label **Current taste**, pill chips (not nested cards). Disambiguation: poster thumbnails with light scrim + short title below; selected state = primary green outline (no gradient text). Motion: only opacity/transform on chip select; layout not animated.
