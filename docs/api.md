# API Reference

Base URL: `http://localhost:8000`

## Health

### GET /healthz

Returns service health and config.

Response:
```json
{
  "status": "ok",
  "redis_ok": true,
  "onnx_ok": true,
  "metadata_ok": true,
  "num_users": 610,
  "num_items": 9724,
  "tfidf_ok": false,
  "model_version": "dev",
  "candidate_pool": 500,
  "cache_ttl_seconds": 300,
  "explain_ttl_seconds": 60,
  "alpha": 0.7
}
```

## Movie Search

### GET /movies/search?q=...

Case-insensitive substring search by title. Returns up to 20 matches.

Response:
```json
[{"movie_id": 1, "title": "Toy Story (1995)"}]
```

## Genres

### GET /genres

Returns all distinct genres.

Response:
```json
[{"name": "Action"}, {"name": "Drama"}]
```

### GET /genres/{genre}/seeds?limit=20

Returns popular seed movies for a genre.

Response:
```json
{"seeds": [{"movie_id": 356, "title": "Forrest Gump (1994)"}]}
```

## Seed Recommendations (Product)

### POST /recommendations

Body:
```json
{"seeds": [356, 260, 318, 1198, 1210], "shuffle": false}
```

Response:
```json
{
  "items": [{"movie_id": 186, "title": "Nine Months (1995)", "score": 0.74}],
  "seed_movies": [{"movie_id": 356, "title": "Forrest Gump (1994)"}],
  "anchor_source": "seed",
  "model_version": "dev"
}
```

### POST /explanations

Body:
```json
{"seeds": [356, 260, 318, 1198, 1210], "shuffle": false}
```

Response:
```json
{
  "user_id": null,
  "model_version": "dev",
  "alpha": 0.7,
  "anchor_movie": {"movie_id": 356, "title": "Forrest Gump (1994)"},
  "seed_movies": [{"movie_id": 356, "title": "Forrest Gump (1994)"}],
  "topk": [
    {"movie_id": 356, "title": "Forrest Gump (1994)", "ncf": 0.0, "content": 0.64, "final": 0.64}
  ],
  "similar_movies": [{"movie_id": 296, "title": "Pulp Fiction (1994)", "similarity": 0.64}],
  "content_available": true,
  "anchor_source": "seed"
}
```

## Debug Endpoints

### GET /recommend
Legacy debug endpoint (user_id + k). Not used by UI.

### GET /explain
Legacy debug endpoint (user_id + k). Not used by UI.

### GET /score
NCF model score for a single user/movie index.

### GET /debug/similar
Content-based similarity for a movie.
