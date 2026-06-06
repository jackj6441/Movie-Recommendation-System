---
target: ChatRecommender conversational RAG chat
total_score: 24
p0_count: 0
p1_count: 2
p2_count: 2
p3_count: 1
timestamp: 2026-06-05T02-56-07Z
slug: web-src-components-chat-chatrecommender-tsx
---
# Critique: Conversational RAG Chat (`ChatRecommender`)

Target: `web/src/components/chat/ChatRecommender.tsx` and related chat surfaces.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Send/Thinking states good; mobile taste collapsed by default hides memory |
| 2 | Match System / Real World | 2 | "Seed Set", "Tonight's strongest match" feel internal/marketing |
| 3 | User Control and Freedom | 3 | Start over + chip × strong; duplicate Start over locations |
| 4 | Consistency and Standards | 2 | Comedy appears in composer chips and taste rail simultaneously |
| 5 | Error Prevention | 2 | 5-seed cap disables cards silently; no inline invalid-genre UX |
| 6 | Recognition Rather Than Recall | 3 | Desktop taste rail helps; mobile relies on closed details |
| 7 | Flexibility and Efficiency | 2 | Enter-to-send only; no power path for refresh/disambiguation |
| 8 | Aesthetic and Minimalist Design | 2 | Hero block + gradients + nested bordered panels add weight |
| 9 | Error Recovery | 3 | Generic chat error + genre retry; no turn-level retry |
| 10 | Help and Documentation | 2 | Home lead only; disambiguation step lacks one-line primer |
| **Total** | | **24/40** | **Needs improvement** |

## Anti-Patterns Verdict

**LLM assessment**: Not blatant AI slop (warm cream/green, system UI font, no gradient text). Still reads as "familiar chat recommender template": bubble thread, rounded composer, hero #1 card with kicker, radial page wash. Cormorant display on brand mark only is fine; the hero-metric shape (#1 + kicker + title) is the strongest cliché signal.

**Deterministic scan**: `detect.mjs` on `web/src/components/chat` returned **0 findings**.

**Browser overlays**: Not run (no mutable browser injection in this session). Assessment based on source + structure.

## Overall Impression

The conversational flow is functionally complete and better than a generic chat wrapper: taste rail, disambiguation posters, and context chips show real product thinking. The biggest gap is **state duplication** (genres in two places, Start over twice) and **mobile taste visibility**. Polish those and the interface will feel intentional rather than assembled.

## What's Working

1. **Desktop taste rail**: Sticky aside keeps seeds/genres/year in view during long threads; directly addresses the PRD v1.2 job-to-be-done.
2. **Poster-forward disambiguation**: Card grid with year/genres beats checkbox list for movie recognition; copy clarifies "not final recommendations."
3. **Turn feedback loop**: Empty-message summaries ("You selected: Comedy"), loading disable, and final-only SSE handling make the thread feel responsive.

## Priority Issues

**[P1] Duplicate genre surfaces (composer vs taste rail)**
- Why: Users cannot tell which Comedy chip is authoritative; removing one does not remove the other until a round-trip completes.
- Fix: Composer genres = draft intent only; taste rail = committed session state. Visually differentiate (e.g. "Draft" vs "Active taste") or sync composer from rail after each final.
- Command: `/impeccable layout`

**[P1] Mobile taste rail hidden in closed `<details>`**
- Why: Jordan and Sam lose "what the system remembers" unless they expand; violates recognition-over-recall for multi-turn chat.
- Fix: Default open after first recommendation; show chip count in summary ("Current taste · 2 seeds, 1 genre"); or pin a one-line summary when collapsed.
- Command: `/impeccable adapt`

**[P2] Product jargon leaks into UI**
- Why: "Use as Seed Set", assistant copy referencing Seed Set, and internal ranking language break match-with-real-world for casual viewers.
- Fix: User-facing "starting movies", "Use these picks", assistant copy without engineer terms.
- Command: `/impeccable clarify`

**[P2] Hero recommendation block dominates chat rhythm**
- Why: Full hero scrim + "#1" + "Tonight's strongest match" competes with assistant prose; time-specific kicker is wrong for afternoon browsing.
- Fix: Lighter chat-native card (title + poster thumb + actions); neutral kicker ("Top pick for you") or drop kicker in-thread.
- Command: `/impeccable distill`

**[P3] No PRODUCT.md / DESIGN.md**
- Why: Tokens exist (`tokens.css`) but no documented scene sentence, register, or component rules; future changes will reintroduce slop.
- Fix: Run `/impeccable teach` + `/impeccable document` to lock product register and chat-specific patterns.
- Command: `/impeccable document`

## Persona Red Flags

**Alex (Power User)**: Two "Start over" buttons (hero + composer) force a choice. Genre must be toggled off in composer for "Show more recommendations" even when taste rail already shows Comedy. Disambiguation multi-select has no Shift+click or keyboard multi-select pattern.

**Jordan (First-Timer)**: "Use as Seed Set" is opaque. Disambiguation grid offers up to 10 posters at once (>4 options). Mobile taste collapsed = no visible memory. Unclear whether disambiguation picks or recommendations are "the answer."

**Sam (Accessibility)**: Poster tiles use `alt=""` (decorative OK if title is adjacent; verify button accessible name includes title+year). `aria-pressed` on poster cards is good. Closed `<details>` may skip taste content from navigation order until expanded.

## Minor Observations

- Page-level radial gradients add atmosphere but cost minimalist product clarity.
- `tokens.css` uses hex neutrals; OKLCH used in newer chat CSS: slight token drift.
- Seed cap at 5: disabled state only, no toast (PRD mentions visible limit message).
- Chat error is network-generic; no distinction for clarification vs hard failure.

## Questions to Consider

- Should composer genre chips disappear once a thread starts, leaving taste rail as the only genre surface?
- Does the hero card need to exist inside the thread, or would a compact top-pick row match chat density better?
- What should mobile users see in one glance without opening "Current taste"?
