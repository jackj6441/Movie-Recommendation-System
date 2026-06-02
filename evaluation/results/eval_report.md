# Evaluation Report

- Project: `movie-recommendation-system`
- Generated at: `2026-06-02T17:05:48.192826+00:00`

## Metrics

- RMSE: `n/a` (product path uses seed + content; NCF not retrained on 32M in this artifact drop)
- Model sample count: `n/a`
- Recall@K: `0.04`
- NDCG@K: `0.01870278651805037`
- Recommendation coverage: `0.017130620985010708`
- Top-K diversity: `0.6297737389770732`
- Popularity baseline Recall@K: `0.03`
- Content baseline Recall@K: `0.04`

## Notes

- Retrieval evaluation used MovieLens 32M ratings with the served catalog (`catalog_movies.csv`, ~23k movies).
- Legacy `model_metrics.json` still reflects the old `ml-latest-small` NCF checkpoint if present.
