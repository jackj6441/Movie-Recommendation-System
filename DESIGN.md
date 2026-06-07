---
name: Living Room Shelf
description: High-fidelity warm living-room UI for chat-based movie recommendations — plaster walls, wooden frames, poster-forward results.
colors:
  page-bg: "oklch(0.92 0.02 75)"
  surface: "oklch(0.97 0.01 82)"
  text-primary: "oklch(0.28 0.012 68)"
  text-muted: "oklch(0.48 0.014 68)"
  border: "oklch(0.8 0.02 72)"
  primary: "oklch(0.45 0.09 145)"
  wood-dark: "oklch(0.38 0.04 62)"
  wood-mid: "oklch(0.52 0.05 68)"
  mat: "oklch(0.97 0.008 85)"
  accent-warn: "oklch(0.58 0.14 45)"
  accent-error: "oklch(0.55 0.18 25)"
typography:
  brand:
    fontFamily: "Caveat, cursive"
    usage: "Logo wordmark only"
  display:
    fontFamily: "Playfair Display, Georgia, serif"
    fontWeight: 600
    usage: "All poster captions (hero, strip, disambiguation)"
  ui:
    fontFamily: "Instrument Sans, system-ui, sans-serif"
    fontWeight: 400
rounded:
  sm: "8px"
  md: "10px"
  lg: "18px"
  pill: "999px"
  frame: "2px"
  frame-hero: "3px"
spacing:
  sm: "0.75rem"
  md: "1rem"
  lg: "1.5rem"
components:
  frame:
    hero-outer: "12px"
    hero-mat: "14px"
    strip-outer: "6px"
    strip-mat: "8px"
    shadow: "{shadow-frame}"
    hero-max-width: "26.25rem"
    strip-tile-width: "7.25rem"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "oklch(0.98 0.008 84)"
    rounded: "50%"
assets:
  plaster-tile: "/assets/living-room/plaster-wall-tile.png"
---

## Overview

**Living Room Shelf** — high-fidelity interior aesthetic. User picks movies at home in warm evening light on a plaster wall. TMDB posters hang in wooden frames with mat borders; secondary picks sit on a wooden shelf. Chat-first product flow (`POST /rag/chat`).

**Fidelity tier:** Photoreal textures + 9-slice wood frames (hybrid with CSS mat/shadow). Decorative sidebar scene on desktop only.

## Colors

Warm plaster wall base (`--color-page-bg: oklch(0.92 0.02 75)`), tiled texture with warm top light and bottom vignette. Deep olive primary (`oklch(0.45 0.09 145)`). Wood system: `--color-wood-dark`, `--color-wood-mid`, `--color-mat`. Active sidebar session: solid primary + white text.

All tokens in `web/src/styles/tokens.css` (OKLCH).

## Typography

- **Caveat**: brand wordmark «Living Room Shelf» + sofa icon.
- **Playfair Display**: all poster captions (hero title, strip titles, disambiguation).
- **Instrument Sans**: buttons, chips, inputs, labels, body, sidebars.
- **IBM Plex Mono**: rank badges and debug metadata.

## Scene & assets

| Asset | Path | Phase |
|---|---|---|
| Plaster wall tile | `public/assets/living-room/plaster-wall-tile.png` | A ✓ |
| Hero frame 9-slice | `frame-hero-9slice.png` (256×256, slice 48) | C ✓ |
| Strip frame 9-slice | `frame-strip-9slice.png` (128×128, slice 24) | C ✓ |
| Wood shelf | `wood-shelf.png` | C ✓ |
| Sidebar cabinet | `sidebar-cabinet.png` | D |

## Frame primitives (Phase C ✓)

Shared `PosterFrame` component: 9-slice wood `border-image` + CSS mat padding + directional shadow.

- Hero: `--frame-outer-hero` 12px, `--frame-mat-hero` 14px, slice 48
- Strip: `--frame-outer-strip` 6px, `--frame-mat-strip` 8px, slice 24
- Captions: Playfair Display on hero, strip, disambiguation titles
- Strip: horizontal scroll (no show-more toggle); frames + captions in aligned rows
- Selected / in-seeds: inset 2px primary on mat

## Icons & chat shell (Phase D ✓)

Inline SVG set wired into UI:

- **Assistant avatar**: olive circle + sofa on each assistant turn
- **Send**: circular primary button + paper plane (`aria-label="Send"`)
- **Composer**: pill wrap, paperclip attach (disabled placeholder)
- **Sidebar**: speech bubble per session, solid green active link, CloseIcon delete
- **Sidebar footer (desktop)**: cabinet scene image + Settings (disabled placeholder)
- **Taste pills**: CloseIcon on removable tags
- **User bubble**: `--color-user-bubble` white/cream

## Stylesheet layout

| File | Scope |
|---|---|
| `tokens.css` | Design tokens + asset URLs |
| `base.css` | Reset, page scene background |
| `shell.css` | App header, tabs, footer |
| `chat.css` | Chat flow, composer, taste rail |
| `results.css` | Hero pick, poster tiles, strip, shelf |
| `evidence.css` | System Evidence tab |
| `global.css` | Import barrel |

## Shell (Phase B)

- **Brand lockup**: `AppBrand` — olive sofa SVG + Caveat wordmark «Living Room Shelf».
- **View tabs**: segment control; active tab uses solid `--color-primary` + white text.
- **Icons**: `web/src/components/icons/` — inline SVG, `currentColor` stroke (used in later phases).

## Phase E (tests & verification ✓)

- `App.test.tsx`: Living Room Shelf brand, composer icons, assistant avatar, frame layers, wood shelf.
- `PosterFrame.test.tsx`: mat/wood DOM + interactive aria labels.
- `MoreMoviesStrip.test.tsx`: shelf + strip frame count.
- Verify: `npm test` + `npm run build`.

## Do's and Don'ts

- Do show skeletons while genres, results, or RAG load.
- Do keep hero poster visibly larger than strip tiles (~3:1 height ratio).
- Do use Playfair only on poster captions, never on buttons/chips.
- Do use plaster tile + gradients on `.page`, not flat fill alone.
- Don't use billboard scrim with oversized title on poster image.
- Don't add right-rail plant bokeh (clutters taste panel).
- Don't nest bordered cards inside chat recommendation blocks.
