---
name: Movie Recommender
description: Hero Shelf — warm evening living-room UI for chat-based movie recommendations with poster-forward results.
colors:
  page-bg: "oklch(0.96 0.012 78)"
  surface: "oklch(0.98 0.008 78)"
  text-primary: "oklch(0.28 0.012 68)"
  text-muted: "oklch(0.48 0.014 68)"
  border: "oklch(0.84 0.018 74)"
  primary: "oklch(0.52 0.1 145)"
  accent-warn: "oklch(0.58 0.14 45)"
  accent-error: "oklch(0.55 0.18 25)"
typography:
  display:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontWeight: 600
    usage: "Empty-state greeting only"
  ui:
    fontFamily: "Instrument Sans, system-ui, sans-serif"
    fontWeight: 400
rounded:
  sm: "8px"
  md: "10px"
  lg: "18px"
  pill: "999px"
  frame: "6px"
  frame-hero: "8px"
spacing:
  sm: "0.75rem"
  md: "1rem"
  lg: "1.5rem"
components:
  frame:
    border: "{frame-border}"
    shadow: "{shadow-frame}"
    hero-max-width: "26.25rem"
    strip-tile-width: "7.25rem"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "oklch(0.98 0.008 84)"
    rounded: "{rounded.sm}"
---

## Overview

**Hero Shelf** aesthetic: user picks movies at home in warm evening light. UI chrome stays quiet; TMDB posters carry emotion. The #1 recommendation uses the largest framed poster; secondary picks appear as smaller frames on a horizontal shelf.

Product flow is **chat-first** (`POST /rag/chat`), not a wizard stepper.

## Colors

Restrained palette on warm gray-beige (`--color-page-bg`). Page uses a soft top vignette and light grain texture. Moss-green primary (`oklch(0.52 0.1 145)`) for active chips, tabs, and primary actions only.

All tokens live in `web/src/styles/tokens.css` as OKLCH values.

## Typography

- **Instrument Sans**: buttons, chips, inputs, labels, body, poster captions, hero title (Phase 1+).
- **Cormorant Garamond**: empty-state greeting (`chat-greeting`) only.
- **IBM Plex Mono**: rank badges and debug metadata.

## Frame primitives

Shared poster presentation (Hero, Strip, Disambiguation):

- `--frame-border`, `--shadow-frame`, `--shadow-frame-hover`
- Selected / in-seeds: `inset 2px` accent border, no outer glow ring
- Hero max width `--hero-max-width` (420px); strip tiles `--strip-tile-width`

## Elevation

Soft directional frame shadows simulate wall-hung posters. Cards (Evidence tab) use `--shadow-lg` with `--color-border-soft`. No glassmorphism.

## Stylesheet layout

| File | Scope |
|---|---|
| `tokens.css` | Design tokens |
| `base.css` | Reset, shared components, animations |
| `shell.css` | App header, tabs, footer |
| `chat.css` | Chat flow, composer, taste rail |
| `results.css` | Hero pick, poster tiles, strip |
| `evidence.css` | System Evidence tab |
| `global.css` | Import barrel |

## Shell & Evidence

- **App header**: Instrument Sans brand line + segment control tabs (`role="tablist"`), no logo pill.
- **Footer**: TMDB attribution as subtle top-bordered footnote.
- **Evidence tab**: Flat cards, compact status strip (not hero-metric 3-up), mono tabular values.

## Do's and Don'ts

- Do show skeletons while genres, results, or RAG load.
- Do retry failed genre fetch with visible error + Retry button.
- Do keep hero poster visibly larger than strip tiles (~3:1 height ratio).
- Don't use billboard scrim with oversized title on the poster image.
- Don't expose raw API field names in user-facing copy.
- Don't use display serif on buttons, chips, or form labels.
- Don't nest bordered cards inside chat recommendation blocks.
