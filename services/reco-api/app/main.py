import json
import os

import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"] ,
    allow_headers=["*"],
)

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
model_version = os.getenv("MODEL_VERSION", "dev")
try:
    redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
except redis.RedisError:
    redis_client = None


@app.get("/healthz")
def healthz() -> dict:
    redis_ok = False
    if redis_client is not None:
        try:
            redis_ok = bool(redis_client.ping())
        except redis.RedisError:
            redis_ok = False
    return {"status": "ok", "redis_ok": redis_ok}


@app.get("/recommend")
def recommend(user_id: int, k: int = 20) -> dict:
    cache_key = f"rec:user:{user_id}:k:{k}"
    cached = None
    if redis_client is not None:
        try:
            cached = redis_client.get(cache_key)
        except redis.RedisError:
            cached = None

    explain = {
        "ncf_score": 4.3,
        "content_score": 0.82,
        "alpha": 0.7,
        "similar_movies": [
            {"movie_id": 201, "title": "Similar Movie 201", "score": 0.91},
            {"movie_id": 202, "title": "Similar Movie 202", "score": 0.88},
            {"movie_id": 203, "title": "Similar Movie 203", "score": 0.86},
        ],
    }

    if cached:
        payload = json.loads(cached)
        payload["cache_hit"] = True
        if "model_version" not in payload:
            payload["model_version"] = model_version
        if "explain" not in payload:
            payload["explain"] = explain
        if redis_client is not None:
            try:
                redis_client.setex(cache_key, 300, json.dumps(payload))
            except redis.RedisError:
                pass
        return payload

    items = [
        {"movie_id": 101, "title": "Mock Movie 101", "score": 4.8},
        {"movie_id": 102, "title": "Mock Movie 102", "score": 4.7},
        {"movie_id": 103, "title": "Mock Movie 103", "score": 4.6},
        {"movie_id": 104, "title": "Mock Movie 104", "score": 4.5},
        {"movie_id": 105, "title": "Mock Movie 105", "score": 4.4},
    ]

    payload = {
        "user_id": user_id,
        "k": k,
        "cache_hit": False,
        "items": items,
        "model_version": model_version,
        "explain": explain,
    }

    if redis_client is not None:
        try:
            redis_client.setex(cache_key, 300, json.dumps(payload))
        except redis.RedisError:
            pass

    return payload


@app.get("/model/version")
def model_version_info() -> dict:
    return {
        "model_version": model_version,
        "runtime": "onnx-placeholder",
        "cache_ttl_seconds": 300,
    }
