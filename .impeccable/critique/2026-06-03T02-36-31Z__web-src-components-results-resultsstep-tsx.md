---
target: results page
total_score: 35
p0_count: 0
p1_count: 1
timestamp: 2026-06-03T02-36-31Z
slug: web-src-components-results-resultsstep-tsx
---
# Critique: Results page (web/src/components/results)

Target: results step — filters, featured grid, more-movies poster grid, empty/error states.
Register: product. Browser overlay unavailable in this environment; design review is code-based, deterministic detector ran clean.

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Filter changes refetch silently; grid keeps stale results with no loading/updating cue. |
| 2 | Match System / Real World | 4 | Natural copy; debug fields removed from main flow. |
| 3 | User Control and Freedom | 4 | Reset filters, Start over, Back, Shuffle all present. |
| 4 | Consistency and Standards | 3 | Results "Topics" duplicates Step-1 "Select Genres" with different label and intent. |
| 5 | Error Prevention | 4 | Single-select decade, constrained genre set, seeds validated upstream. |
| 6 | Recognition Rather Than Recall | 4 | Filters and seeds stay visible; active states clear. |
| 7 | Flexibility and Efficiency | 3 | No keyboard shortcuts, no filter deep-link, no quick clear besides reset. |
| 8 | Aesthetic and Minimalist Design | 3 | Cleaner after removing Why/Score cards, but up to 19 topic chips is a wall. |
| 9 | Error Recovery | 4 | Plain, actionable error + empty-state copy with reset. |
| 10 | Help and Documentation | 3 | Subtitles act as hints; "ranked by the same model" is vague. |
| **Total** | | **35/40** | **Good (top of band)** |

## Anti-Patterns Verdict

LLM: Passes the "AI made this" test. Warm cream surface, serif headings, poster scrim gradient — a deliberate, on-brand choice that avoids the dark-neon streaming reflex (an explicit anti-reference). No gradient text, glassmorphism, side-stripe borders, hero-metric template, or identical icon-card grids. Three stacked cards, not nested. No em dashes in new copy.

Deterministic scan: detect.mjs on web/src/components/results returned 0 findings.

Visual overlays: not available (no browser injection in this environment); fallback to code review.

## Overall Impression

The cleanup is the win: dropping the "Why these movies?" summary and Score breakdown, plus the poster grid, turns a debug-flavored page into a poster-forward gallery that matches the product story. The biggest remaining gap is feedback honesty — when a filter changes, the page silently swaps results with no visible "updating" state, so users (and screen readers) can't tell the filter took effect.

## What's Working

- Poster-forward results: 2:3 tiles with scrim + serif titles read as a film gallery, on-brand and recognizable.
- Strong escape routes: Reset filters, Start over, Back, Shuffle — user is never trapped.
- Good empty/error copy: plain-language, actionable, no exposed internals.

## Priority Issues

- [P1] Silent filter refetch. Changing a decade/topic debounces then swaps the grid with no loading affordance (data isn't cleared, so no skeleton). Chips disable and Shuffle reads "Shuffling…", but the grid itself gives no signal. Users may think nothing happened and re-toggle. Fix: show a dim/skeleton or subtle "Updating results…" on the grid whenever loading, even when prior data exists; add aria-live so the change is announced. Command: /impeccable harden.
- [P2] Topic filter is a wall of options. Up to 19 genre chips always visible breaks the ≤4 working-memory guideline and duplicates Step-1 genres conceptually. Fix: show a few priority topics with a "More" disclosure, or cap visible chips. Command: /impeccable distill.
- [P2] Sub-44px touch targets. Chips (~30px tall) fall below the 44×44 minimum for mobile/motor users. Fix: raise chip min-height/padding to 44px. Command: /impeccable adapt.
- [P3] Featured silently re-ranks under filters with no label. The top-3 changes when filtering, but nothing signals it's filtered. Fix: small "Filtered by …" note near the Featured subtitle. Command: /impeccable clarify.
- [P3] Misleading Shuffle copy and dual reset. Shuffle reads "Shuffling…" during filter refetch; the no-match state shows two Reset buttons. Command: /impeccable polish.

## Persona Red Flags

Sam (accessibility-dependent): focus indicators exist globally and chips expose aria-pressed in labeled groups — good. But the results grid has no aria-live region, so filter-driven result changes are not announced; a screen-reader user can't tell the filter applied.

Riley (stress tester): empty state recovers gracefully. But the whole wizard lives in React state — a mid-flow refresh or shared-link loses seeds, filters, and results entirely.

Casey (distracted mobile / project "casual demo user"): primary actions (Shuffle/Start over/Back) sit mid-card, not in the thumb zone; chips are small and close together; state is lost on tab switch. Posters are recognizable, which helps, but the long topic list is heavy on a phone.

## Minor Observations

- "Topics" (results) vs "Select Genres" (Step 1) naming inconsistency for the same control.
- No match count; users can't see how many results a filter produced.
- "ranked by the same model" subtitle is vague for a casual audience.

## Questions to Consider

- What would tell a user, at a glance, that a filter just took effect and these are the filtered picks?
- Does the results page need all 19 genres, or would 5-6 priority topics plus "More" cover the demo story?
- Should filter + seed state survive a refresh or a shared link, given this is a portfolio demo people will revisit?
