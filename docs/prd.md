# PRD (Condensed)

## Overview

AI-powered Movie Recommendation System with hybrid ranking (NCF + content embeddings), low-latency serving, and explainable UI.

## Goals

- Quality: RMSE <= 0.82 on MovieLens 1M (explicit rating).
- Performance: p99 latency < 50 ms with caching and ONNX Runtime.
- Explainability: show similarity reasons and score contributions.
- Reproducibility: end-to-end pipeline from data prep -> train -> export -> serve -> UI.

## Non-Goals

- No large-scale distributed training.
- No online learning/rl in v1.
- No ads or multi-objective optimization in v1.

## Users & Scenarios

- End users: get top-N recommendations, see why a movie is suggested.
- Operators: compare strategy variants, inspect latency/cache hit rate.

## Core Product Flow (Current)

1. Open the chat-first recommender UI.
2. Optionally pick up to three genre chips and describe taste in natural language.
3. Receive streaming assistant text plus up to 24 ranked recommendations (multi-retriever fusion).

## Functional Requirements

- Search: case-insensitive substring search by title.
- Seed-based recommendations: use content embeddings to score candidates.
- Explainability: per-item contributions (ncf/content/final) and similar movies.
- Health checks: /healthz.

## Data

- MovieLens small (ml-latest-small) for dev.
- Required files: movies.csv, ratings.csv, links.csv (optional).

## Metrics

- Offline: RMSE on explicit ratings.
- Online: latency, cache hit ratio, error rate.

## Risks & Mitigations

- Sparse content: use title + genres; upgrade to transformer embeddings.
- Latency: cache + ONNX Runtime.
- Explainability trust: show signal sources (NCF vs content) clearly.
