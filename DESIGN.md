---
name: Movie Recommender
description: Warm light product UI for seed-based movie recommendations with poster-forward results.
colors:
  page-bg: "#fbfaf7"
  surface: "#ffffff"
  surface-muted: "#fffdf9"
  text-primary: "#2b2a28"
  text-muted: "#6a655f"
  text-subtle: "#7b746d"
  border: "#d7cfc4"
  border-soft: "#efe7db"
  primary: "#2f855a"
  primary-hover: "#3a9b6c"
  accent-warn: "#c05621"
  accent-error: "#c53030"
  chart-ncf: "#2f855a"
  chart-content: "#c05621"
  baseline: "#8aa6c2"
typography:
  display:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontWeight: 600
  ui:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif"
    fontWeight: 400
rounded:
  sm: "8px"
  md: "10px"
  lg: "18px"
  pill: "999px"
spacing:
  sm: "0.55rem"
  md: "1rem"
  lg: "1.75rem"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "0.5rem 1rem"
  chip:
    backgroundColor: "{colors.surface-muted}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.pill}"
    padding: "0.35rem 0.85rem"
---

## Overview

Restrained product UI: warm off-white page, green primary actions, TMDB posters as visual hero on results. Wizard uses clear stepper and system fonts for all interactive chrome.

## Colors

Page background uses subtle warm radial washes over `#fbfaf7`. Surfaces are warm white (`#ffffff`, `#fffdf9`). Primary green `#2f855a` for active chips, tabs, and collaborative chart bars. Orange `#c05621` for warnings and content signal bars.

## Typography

Cormorant Garamond for `h1`, `h2`, `h3` only. All buttons, chips, inputs, labels, and body copy use the system-ui stack at 0.875–1rem.

## Elevation

Cards use soft border `#efe7db` and shadow `0 20px 36px rgba(39, 30, 14, 0.08)`. Dropdowns use stronger shadow for lift. No glassmorphism.

## Components

- **Chip:** pill toggle, `aria-pressed`, active = primary fill.
- **Card:** 18px radius, 1.75rem padding.
- **Movie card:** poster background + bottom scrim gradient; fallback gradient when no poster.
- **Stepper:** numbered steps with connector line; current step emphasized.

## Do's and Don'ts

- Do show skeletons while genres, results, or RAG load.
- Do retry failed genre fetch with visible error + Retry button.
- Don't expose raw API field names in wizard subtitles.
- Don't use display serif on buttons, chips, or form labels.
- Don't add decorative grid overlay when a real poster is shown.
