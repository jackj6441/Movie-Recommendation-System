# Movie Recommender — Product Context

## Register

product

## Product Purpose

A portfolio-grade movie recommendation demo: users pick genres and seed movies, receive content-based recommendations with AI explanations, and reviewers can inspect ML system evidence (health, metrics, benchmarks).

## Target Users

- **Portfolio reviewers / ML Infra interviewers:** evaluate serving, observability, evaluation artifacts, and deployment proof via System Evidence tab.
- **Casual demo users:** pick a few movies at home and explore recommendations with poster-rich UI.

## Success Criteria

- Complete wizard flow (genres → seeds → results) without confusion.
- Posters and titles make movies recognizable at a glance.
- Evidence tab communicates system quality without exposing debug API noise in the main flow.

## Brand Personality

Warm, calm, trustworthy. Evening-at-home movie picking, not blockbuster hype.

## Anti-References

- Dark neon streaming clone aesthetics.
- Generic SaaS purple-gradient hero dashboards.
- Debug metadata (`model_version`, `alpha`) in user-facing wizard copy.
- Fake static UI chips masquerading as dynamic data.

## Strategic Design Principles

1. Posters carry emotional weight; UI chrome stays restrained.
2. System-ui typography for controls; display serif for headings only.
3. Loading and error states are first-class, never silent failures.
4. Evidence tab is for operators; recommender tab is for the product story.
