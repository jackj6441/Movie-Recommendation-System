import csv
import json
import os
import time

import numpy as np
import onnxruntime as ort
import redis
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from app import content, metrics, rag, seed_ranker

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def cors_allowed_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOW_ORIGINS", "")
    origins = [*DEFAULT_CORS_ORIGINS]
    origins.extend(
        origin.strip().rstrip("/")
        for origin in configured.split(",")
        if origin.strip()
    )
    return list(dict.fromkeys(origins))


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    # Covers any Vite dev port (5173 default + 5174-5179 fallbacks)
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):517[0-9]",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def record_http_metrics(request, call_next):
    started_at = time.perf_counter()
    response = await call_next(request)
    latency_ms = (time.perf_counter() - started_at) * 1000
    metrics.record_request(request.url.path, response.status_code, latency_ms)
    return response

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
model_version = os.getenv("MODEL_VERSION", "dev")
movies_csv_path = os.getenv("MOVIES_CSV_PATH", "ml-latest-small/movies.csv")
ratings_csv_path = os.getenv("RATINGS_CSV_PATH", "ml-latest-small/ratings.csv")
onnx_model_path = os.getenv("ONNX_MODEL_PATH", "models/ncf.onnx")
metadata_path = os.getenv("METADATA_PATH", "models/metadata.json")
candidate_pool = int(os.getenv("CANDIDATE_POOL", "500"))
cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "300"))
explain_ttl_seconds = int(os.getenv("EXPLAIN_TTL_SECONDS", "60"))
alpha = float(os.getenv("ALPHA", "0.7"))
try:
    redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
except redis.RedisError:
    redis_client = None

num_users = int(os.getenv("NUM_USERS", "10000"))
num_items = int(os.getenv("NUM_ITEMS", "10000"))
user_id_to_idx: dict[str, int] = {}
movie_id_to_idx: dict[str, int] = {}
metadata_ok = False
if os.path.exists(metadata_path):
    try:
        with open(metadata_path, encoding="utf-8") as metadata_file:
            metadata = json.load(metadata_file)
            num_users = int(metadata.get("num_users", num_users))
            num_items = int(metadata.get("num_items", num_items))
            user_id_to_idx = {
                str(key): int(value)
                for key, value in metadata.get("user_id_to_idx", {}).items()
            }
            movie_id_to_idx = {
                str(key): int(value)
                for key, value in metadata.get("movie_id_to_idx", {}).items()
            }
            metadata_ok = True
    except (OSError, ValueError):
        print(f"Warning: failed to load metadata at {metadata_path}")

try:
    onnx_session = ort.InferenceSession(onnx_model_path, providers=["CPUExecutionProvider"])
except Exception:
    onnx_session = None
    print(f"Warning: failed to load ONNX model at {onnx_model_path}")

content_ok = False

movie_titles: dict[int, str] = {}
movie_genres: dict[int, list[str]] = {}
all_genres: set[str] = set()
try:
    with open(movies_csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            movie_id = int(row.get("movieId", "0"))
            title = row.get("title", "").strip()
            genres_value = row.get("genres", "")
            if movie_id and title:
                movie_titles[movie_id] = title
                genre_list = [g for g in genres_value.split("|") if g and g != "(no genres listed)"]
                movie_genres[movie_id] = genre_list
                all_genres.update(genre_list)
except OSError:
    print(f"Warning: failed to load movies CSV at {movies_csv_path}")

movie_popularity: dict[int, int] = {}
ratings_user_ids: set[int] = set()
ratings_movie_ids: set[int] = set()
try:
    with open(ratings_csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            user_id = int(row.get("userId", "0"))
            movie_id = int(row.get("movieId", "0"))
            if user_id:
                ratings_user_ids.add(user_id)
            if movie_id:
                ratings_movie_ids.add(movie_id)
                movie_popularity[movie_id] = movie_popularity.get(movie_id, 0) + 1
except OSError:
    print(f"Warning: failed to load ratings CSV at {ratings_csv_path}")

if ratings_user_ids:
    num_users = len(ratings_user_ids)
if ratings_movie_ids:
    num_items = len(ratings_movie_ids)

popular_movie_ids = [
    movie_id
    for movie_id, _ in sorted(movie_popularity.items(), key=lambda item: item[1], reverse=True)
]

catalog = seed_ranker.Catalog(
    movie_titles=movie_titles,
    popular_movie_ids=popular_movie_ids,
    candidate_pool=candidate_pool,
)


def get_popular_movies(movie_ids: list[int], limit: int) -> list[int]:
    ranked = sorted(movie_ids, key=lambda mid: movie_popularity.get(mid, 0), reverse=True)
    return ranked[:limit]


def get_title(movie_id: int) -> str:
    return movie_titles.get(movie_id, f"Movie {movie_id}")


def get_ranked_movie_ids() -> list[int]:
    if popular_movie_ids:
        return popular_movie_ids
    if movie_titles:
        return sorted(movie_titles.keys())
    return []



@app.get("/healthz")
def healthz() -> dict:
    redis_ok = False
    if redis_client is not None:
        try:
            redis_ok = bool(redis_client.ping())
        except redis.RedisError:
            redis_ok = False
    return {
        "status": "ok",
        "redis_ok": redis_ok,
        "onnx_ok": onnx_session is not None,
        "metadata_ok": metadata_ok,
        "num_users": num_users,
        "num_items": num_items,
        "tfidf_ok": content_ok,
        "model_version": model_version,
        "candidate_pool": candidate_pool,
        "cache_ttl_seconds": cache_ttl_seconds,
        "explain_ttl_seconds": explain_ttl_seconds,
        "alpha": alpha,
    }


@app.get("/metrics")
def metrics_endpoint() -> Response:
    return Response(content=metrics.prometheus_text(), media_type="text/plain")


@app.get("/genres")
def list_genres():
    return [{"name": genre} for genre in sorted(all_genres)]


@app.get("/genres/{genre}/seeds")
def genre_seeds(genre: str, limit: int = 20):
    genre_key = genre.strip().lower()
    if not genre_key:
        return {"seeds": []}

    if genre_key == "all":
        movie_ids = list(movie_titles.keys())
    else:
        movie_ids = [
            movie_id
            for movie_id, genres in movie_genres.items()
            if any(g.lower() == genre_key for g in genres)
        ]

    movie_ids = get_popular_movies(movie_ids, limit)
    return {
        "seeds": [
            {"movie_id": movie_id, "title": get_title(movie_id)} for movie_id in movie_ids
        ]
    }


@app.get("/movies/search")
def movie_search(q: str = ""):
    query = q.strip().lower()
    if not query:
        return []
    results = []
    for movie_id, title in movie_titles.items():
        if query in title.lower():
            results.append({"movie_id": movie_id, "title": title})
            if len(results) >= 20:
                break
    return results


class SeedsRequest(BaseModel):
    seeds: list[int]
    shuffle: bool = False


@app.get("/score")
def score(user_id: int, movie_id: int):
    if onnx_session is None:
        return JSONResponse(
            status_code=503,
            content={
                "onnx_unavailable": True,
                "model_version": model_version,
                "runtime": "onnxruntime",
            },
        )

    user_key = str(user_id)
    movie_key = str(movie_id)
    if user_key not in user_id_to_idx:
        return JSONResponse(
            status_code=404,
            content={
                "cold_start": True,
                "reason": "user_not_found",
                "model_version": model_version,
                "runtime": "onnxruntime",
            },
        )
    if movie_key not in movie_id_to_idx:
        return JSONResponse(
            status_code=404,
            content={
                "cold_start": True,
                "reason": "movie_not_found",
                "model_version": model_version,
                "runtime": "onnxruntime",
            },
        )

    user_idx = user_id_to_idx[user_key]
    item_idx = movie_id_to_idx[movie_key]
    ort_inputs = {
        "user_idx": np.array([user_idx], dtype=np.int64),
        "item_idx": np.array([item_idx], dtype=np.int64),
    }
    pred = onnx_session.run(["pred_rating"], ort_inputs)[0][0]
    return {
        "user_id": user_id,
        "movie_id": movie_id,
        "pred_rating": float(pred),
        "model_version": model_version,
        "runtime": "onnxruntime",
    }


@app.get("/recommend")
def recommend(user_id: int, k: int = 20) -> dict:
    cache_key = f"rec:{model_version}:user:{user_id}:k:{k}"
    cached = None
    if redis_client is not None:
        try:
            cached = redis_client.get(cache_key)
        except redis.RedisError:
            cached = None

    if cached:
        metrics.record_cache_event("redis", "hit")
        payload = json.loads(cached)
        payload["cache_hit"] = True
        if "model_version" not in payload:
            payload["model_version"] = model_version
        if redis_client is not None:
            try:
                redis_client.setex(cache_key, cache_ttl_seconds, json.dumps(payload))
            except redis.RedisError:
                pass
        return payload
    if redis_client is not None:
        metrics.record_cache_event("redis", "miss")

    ranked_ids = get_ranked_movie_ids()
    items_needed = max(k, 5)

    user_key = str(user_id)
    if user_key not in user_id_to_idx:
        items_ids = ranked_ids[:items_needed]
        if len(items_ids) < items_needed:
            next_id = 1
            while len(items_ids) < items_needed:
                if next_id not in items_ids:
                    items_ids.append(next_id)
                next_id += 1

        similar_ids = ranked_ids[items_needed : items_needed + 3]
        if len(similar_ids) < 3:
            next_id = 1
            while len(similar_ids) < 3:
                if next_id not in items_ids and next_id not in similar_ids:
                    similar_ids.append(next_id)
                next_id += 1

        items = [
            {"movie_id": movie_id, "title": get_title(movie_id), "score": score}
            for movie_id, score in zip(items_ids, [4.8, 4.7, 4.6, 4.5, 4.4], strict=False)
        ]
        explain = {
            "ncf_score": 4.3,
            "content_score": 0.0,
            "alpha": alpha,
            "similar_movies": [
                {"movie_id": movie_id, "title": get_title(movie_id), "score": score}
                for movie_id, score in zip(similar_ids, [0.91, 0.88, 0.86], strict=False)
            ],
        }
        cold_start = True
    elif onnx_session is not None and ranked_ids and movie_id_to_idx:
        candidate_ids = [mid for mid in ranked_ids[:candidate_pool] if str(mid) in movie_id_to_idx]
        user_idx = user_id_to_idx[user_key]
        item_indices = np.array([movie_id_to_idx[str(mid)] for mid in candidate_ids], dtype=np.int64)
        user_indices = np.full_like(item_indices, user_idx)
        ort_inputs = {"user_idx": user_indices, "item_idx": item_indices}
        scores = onnx_session.run(["pred_rating"], ort_inputs)[0]

        top_k = min(k, len(candidate_ids))
        top_indices = np.argsort(scores)[::-1][:top_k]
        anchor_movie_id = int(candidate_ids[top_indices[0]]) if len(top_indices) else candidate_ids[0]

        content_scores = scores * 0.0
        similar_movies: list[dict] = []
        content_score_value = 0.0
        try:
            content_scores = np.array(
                content.get_similarity_scores(anchor_movie_id, candidate_ids), dtype=np.float32
            )
            similar = content.get_similar(anchor_movie_id, topn=3)
            similar_movies = [
                {"movie_id": mid, "title": get_title(mid), "score": sim}
                for mid, sim in similar
            ]
            top_similar = content.get_similar(anchor_movie_id, topn=10)
            if top_similar:
                content_score_value = float(
                    sum(sim for _, sim in top_similar) / len(top_similar)
                )
            global content_ok
            content_ok = True
        except Exception:
            content_scores = scores * 0.0
            similar_movies = []
            content_score_value = 0.0

        final_scores = alpha * scores + (1 - alpha) * content_scores
        final_top_indices = np.argsort(final_scores)[::-1][:top_k]
        items = [
            {
                "movie_id": int(candidate_ids[idx]),
                "title": get_title(int(candidate_ids[idx])),
                "score": float(final_scores[idx]),
            }
            for idx in final_top_indices
        ]
        if not similar_movies:
            similar_movies = items[:3]
        explain = {
            "ncf_score": float(scores[top_indices[0]]) if len(top_indices) else 0.0,
            "content_score": content_score_value,
            "alpha": alpha,
            "similar_movies": similar_movies,
        }
        cold_start = False
    else:
        items_ids = ranked_ids[:items_needed]
        if len(items_ids) < items_needed:
            next_id = 1
            while len(items_ids) < items_needed:
                if next_id not in items_ids:
                    items_ids.append(next_id)
                next_id += 1

        similar_ids = ranked_ids[items_needed : items_needed + 3]
        if len(similar_ids) < 3:
            next_id = 1
            while len(similar_ids) < 3:
                if next_id not in items_ids and next_id not in similar_ids:
                    similar_ids.append(next_id)
                next_id += 1

        items = [
            {"movie_id": movie_id, "title": get_title(movie_id), "score": score}
            for movie_id, score in zip(items_ids, [4.8, 4.7, 4.6, 4.5, 4.4], strict=False)
        ]
        explain = {
            "ncf_score": 4.3,
            "content_score": 0.0,
            "alpha": alpha,
            "similar_movies": [
                {"movie_id": movie_id, "title": get_title(movie_id), "score": score}
                for movie_id, score in zip(similar_ids, [0.91, 0.88, 0.86], strict=False)
            ],
        }
        cold_start = False

    payload = {
        "user_id": user_id,
        "k": k,
        "cache_hit": False,
        "items": items,
        "model_version": model_version,
        "explain": explain,
        "cold_start": cold_start,
    }

    if redis_client is not None:
        try:
            redis_client.setex(cache_key, cache_ttl_seconds, json.dumps(payload))
        except redis.RedisError:
            pass

    return payload


@app.post("/recommendations")
def recommendations(request: SeedsRequest):
    if not request.seeds or len(request.seeds) > 5:
        return JSONResponse(status_code=400, content={"detail": "seeds must be 1 to 5 items"})

    try:
        result = seed_ranker.rank(request.seeds, request.shuffle, catalog)
    except seed_ranker.InvalidSeedsError:
        return JSONResponse(status_code=400, content={"detail": "no valid seeds"})
    except seed_ranker.ContentUnavailableError:
        return JSONResponse(status_code=503, content={"content_unavailable": True})

    if not result.items:
        return {"items": [], "seed_movies": [], "anchor_source": "seed", "model_version": model_version}

    return {
        "items": [
            {"movie_id": item.movie_id, "title": item.title, "score": item.content_score}
            for item in result.items
        ],
        "seed_movies": [{"movie_id": mid, "title": get_title(mid)} for mid in result.seed_movie_ids],
        "anchor_source": "seed",
        "model_version": model_version,
    }


@app.post("/explanations")
def explanations(request: SeedsRequest):
    if not request.seeds or len(request.seeds) > 5:
        return JSONResponse(status_code=400, content={"detail": "seeds must be 1 to 5 items"})

    try:
        result = seed_ranker.rank(request.seeds, request.shuffle, catalog)
    except seed_ranker.InvalidSeedsError:
        return JSONResponse(status_code=400, content={"detail": "no valid seeds"})
    except seed_ranker.ContentUnavailableError:
        return JSONResponse(status_code=503, content={"content_unavailable": True})

    topk = [
        {
            "movie_id": item.movie_id,
            "title": item.title,
            "ncf": 0.0,
            "content": item.content_score,
            "final": item.content_score,
        }
        for item in result.items
    ]
    similar_movies = [
        {"movie_id": mid, "title": get_title(mid), "similarity": sim}
        for mid, sim in result.similar_movies
    ]
    seed_movies = [{"movie_id": mid, "title": get_title(mid)} for mid in result.seed_movie_ids]
    return {
        "user_id": None,
        "model_version": model_version,
        "alpha": alpha,
        "anchor_movie": {
            "movie_id": result.anchor_movie_id,
            "title": get_title(result.anchor_movie_id),
        },
        "seed_movies": seed_movies,
        "topk": topk,
        "similar_movies": similar_movies,
        "content_available": True,
        "anchor_source": "seed",
    }


@app.post("/rag/explanations")
def rag_explanations(request: SeedsRequest):
    deterministic = explanations(request)
    if isinstance(deterministic, JSONResponse):
        return deterministic

    current_model_version = os.getenv("MODEL_VERSION", model_version)
    return rag.build_mock_structured_explanation(deterministic, current_model_version)


@app.get("/explain")
def explain(user_id: int, k: int = 10):
    cache_key = f"explain:{model_version}:user:{user_id}:k:{k}"
    cached = None
    if redis_client is not None:
        try:
            cached = redis_client.get(cache_key)
        except redis.RedisError:
            cached = None

    if cached:
        metrics.record_cache_event("redis", "hit")
        payload = json.loads(cached)
        return payload
    if redis_client is not None:
        metrics.record_cache_event("redis", "miss")

    ranked_ids = get_ranked_movie_ids()
    top_k = max(k, 1)
    content_available = True

    user_key = str(user_id)
    if user_key not in user_id_to_idx:
        items_ids = ranked_ids[:top_k]
        topk_items = [
            {
                "movie_id": movie_id,
                "title": get_title(movie_id),
                "ncf": score,
                "content": 0.0,
                "final": score,
            }
            for movie_id, score in zip(items_ids, [4.8, 4.7, 4.6, 4.5, 4.4], strict=False)
        ]
        anchor_movie_id = items_ids[0] if items_ids else None
        similar_movies = []
        content_available = False
    elif onnx_session is not None and ranked_ids and movie_id_to_idx:
        candidate_ids = [mid for mid in ranked_ids[:candidate_pool] if str(mid) in movie_id_to_idx]
        user_idx = user_id_to_idx[user_key]
        item_indices = np.array([movie_id_to_idx[str(mid)] for mid in candidate_ids], dtype=np.int64)
        user_indices = np.full_like(item_indices, user_idx)
        ort_inputs = {"user_idx": user_indices, "item_idx": item_indices}
        scores = onnx_session.run(["pred_rating"], ort_inputs)[0]

        anchor_movie_id = int(candidate_ids[int(np.argmax(scores))]) if len(scores) else None
        content_scores = scores * 0.0
        try:
            if anchor_movie_id is not None:
                content_scores = np.array(
                    content.get_similarity_scores(anchor_movie_id, candidate_ids), dtype=np.float32
                )
                global content_ok
                content_ok = True
            else:
                content_available = False
        except Exception:
            content_scores = scores * 0.0
            content_available = False

        final_scores = alpha * scores + (1 - alpha) * content_scores
        top_indices = np.argsort(final_scores)[::-1][:top_k]
        topk_items = [
            {
                "movie_id": int(candidate_ids[idx]),
                "title": get_title(int(candidate_ids[idx])),
                "ncf": float(scores[idx]),
                "content": float(content_scores[idx]),
                "final": float(final_scores[idx]),
            }
            for idx in top_indices
        ]

        similar_movies = []
        if content_available and anchor_movie_id is not None:
            try:
                similar = content.get_similar(anchor_movie_id, topn=3)
                similar_movies = [
                    {"movie_id": mid, "title": get_title(mid), "similarity": sim}
                    for mid, sim in similar
                ]
            except Exception:
                content_available = False
                similar_movies = []
    else:
        items_ids = ranked_ids[:top_k]
        topk_items = [
            {
                "movie_id": movie_id,
                "title": get_title(movie_id),
                "ncf": score,
                "content": 0.0,
                "final": score,
            }
            for movie_id, score in zip(items_ids, [4.8, 4.7, 4.6, 4.5, 4.4], strict=False)
        ]
        anchor_movie_id = items_ids[0] if items_ids else None
        similar_movies = []
        content_available = False

    anchor_movie = None
    if anchor_movie_id is not None:
        anchor_movie = {"movie_id": anchor_movie_id, "title": get_title(anchor_movie_id)}

    payload = {
        "user_id": user_id,
        "model_version": model_version,
        "alpha": alpha,
        "anchor_movie": anchor_movie,
        "topk": topk_items,
        "similar_movies": similar_movies,
        "content_available": content_available,
    }

    if redis_client is not None:
        try:
            redis_client.setex(cache_key, explain_ttl_seconds, json.dumps(payload))
        except redis.RedisError:
            pass

    return payload


@app.get("/debug/similar")
def debug_similar(movie_id: int, topn: int = 5):
    similar = []
    try:
        similar = content.get_similar(movie_id, topn=topn)
    except Exception:
        similar = []

    return {
        "anchor_movie": {"movie_id": movie_id, "title": get_title(movie_id)},
        "topn": [
            {"movie_id": mid, "title": get_title(mid), "similarity": sim}
            for mid, sim in similar
        ],
    }


@app.get("/model/version")
def model_version_info() -> dict:
    return {
        "model_version": model_version,
        "runtime": "onnx-placeholder",
        "cache_ttl_seconds": 300,
    }
