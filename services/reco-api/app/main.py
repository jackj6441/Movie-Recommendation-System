import csv
import json
import os
import re
import time
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from app import artifacts, content, metrics, posters, rag, seed_ranker

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
    # Vite dev: 5173+ fallbacks and this app's 3000+ when ports are already taken
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):(300[0-9]|517[0-9])",
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


model_version = os.getenv("MODEL_VERSION", "dev")
movies_csv_path = os.getenv("MOVIES_CSV_PATH", "models/catalog_movies.csv")
ratings_csv_path = os.getenv("RATINGS_CSV_PATH", "ml-latest-small/ratings.csv")
serving_stats_path = os.getenv("SERVING_STATS_PATH", "models/serving_stats.json")
poster_urls_path = os.getenv("POSTER_URLS_PATH", "models/poster_urls.json")
poster_meta_path = os.getenv("POSTER_META_PATH", "models/poster_meta.json")
default_system_evidence_path = Path(__file__).resolve().parents[1] / "evidence" / "system_evidence.json"
system_evidence_path = os.getenv("SYSTEM_EVIDENCE_PATH", str(default_system_evidence_path))
candidate_pool = int(os.getenv("CANDIDATE_POOL", "500"))

num_users = int(os.getenv("NUM_USERS", "0"))
num_items = int(os.getenv("NUM_ITEMS", "0"))

content_ok = False
try:
    content._load_embeddings()
    content_ok = True
except Exception:
    print("Warning: content embeddings unavailable at startup")

_YEAR_RE = re.compile(r"\((\d{4})\)")


def parse_year(title: str) -> int | None:
    matches = _YEAR_RE.findall(title)
    return int(matches[-1]) if matches else None


movie_titles: dict[int, str] = {}
movie_genres: dict[int, list[str]] = {}
movie_years: dict[int, int] = {}
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
                year = parse_year(title)
                if year is not None:
                    movie_years[movie_id] = year
except OSError:
    print(f"Warning: failed to load movies CSV at {movies_csv_path}")

poster_lookup = posters.load_poster_lookup(poster_urls_path)
poster_meta = posters.load_poster_meta(poster_meta_path)
if not poster_lookup and os.path.exists(poster_urls_path):
    print(f"Warning: poster lookup at {poster_urls_path} is empty or unreadable")
elif not os.path.exists(poster_urls_path):
    print(f"Warning: poster lookup not found at {poster_urls_path}")

movie_popularity: dict[int, int] = {}
popular_movie_ids: list[int] = []
serving_stats_loaded = False
if os.path.exists(serving_stats_path):
    try:
        with open(serving_stats_path, encoding="utf-8") as stats_file:
            stats = json.load(stats_file)
        movie_popularity = {
            int(key): int(value)
            for key, value in stats.get("movie_popularity", {}).items()
        }
        popular_movie_ids = [int(mid) for mid in stats.get("popular_movie_ids", [])]
        num_users = int(stats.get("num_users", num_users))
        num_items = int(stats.get("num_items", num_items))
        serving_stats_loaded = True
    except (OSError, ValueError):
        print(f"Warning: failed to load serving stats at {serving_stats_path}")

if not serving_stats_loaded:
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
    movie_genres=movie_genres,
    movie_years=movie_years,
    movie_popularity=movie_popularity,
)


def get_popular_movies(movie_ids: list[int], limit: int) -> list[int]:
    ranked = sorted(movie_ids, key=lambda mid: movie_popularity.get(mid, 0), reverse=True)
    return ranked[:limit]


def get_title(movie_id: int) -> str:
    return movie_titles.get(movie_id, f"Movie {movie_id}")


def movie_payload(movie_id: int, **fields) -> dict:
    payload = {"movie_id": movie_id, "title": get_title(movie_id), **fields}
    return posters.enrich_movie(movie_id, payload, poster_lookup)


def serving_status() -> dict:
    status = {
        "status": "ok",
        "content_ok": content_ok,
        "catalog_ok": bool(movie_titles),
        "num_users": num_users,
        "num_items": num_items,
        "model_version": model_version,
        "candidate_pool": candidate_pool,
        "ranking_mode": "multi_retriever_fusion",
    }
    status.update(artifacts.fusion_health())
    status.update(
        posters.poster_health_fields(poster_lookup, poster_meta, len(movie_titles))
    )
    return status


def load_system_evidence() -> dict:
    with open(system_evidence_path, encoding="utf-8") as evidence_file:
        return json.load(evidence_file)


def system_evidence_fallback(reason: str) -> dict:
    return {
        "system_name": "movie-recommendation-system",
        "evidence_available": False,
        "evidence_error": reason,
        "serving": serving_status(),
        "model_truth": {
            "product_ranking_path": "Seed Set recommendations via multi-retriever fusion (content, SVD, item-CF, pop)",
            "roadmap": "Optional LightGBM Lambdarank reranker after Phase 1 acceptance",
        },
        "rag": {
            "public_provider": os.getenv("RAG_PROVIDER", "mock"),
            "secret_policy": "real provider keys stay backend-only and are not committed",
        },
    }


@app.get("/healthz")
def healthz() -> dict:
    return serving_status()


@app.get("/system/evidence")
def system_evidence() -> dict:
    try:
        evidence = load_system_evidence()
    except FileNotFoundError:
        return system_evidence_fallback("system evidence artifact not found")
    except (OSError, json.JSONDecodeError):
        return system_evidence_fallback("system evidence artifact unreadable")

    payload = {"evidence_available": True, **evidence}
    payload["serving"] = serving_status()
    payload.setdefault("rag", {})
    payload["rag"]["public_provider"] = os.getenv("RAG_PROVIDER", payload["rag"].get("public_provider", "mock"))
    return payload


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
        "seeds": [movie_payload(movie_id) for movie_id in movie_ids]
    }


@app.get("/movies/search")
def movie_search(q: str = ""):
    query = q.strip().lower()
    if not query:
        return []
    results = []
    for movie_id, title in movie_titles.items():
        if query in title.lower():
            results.append(posters.enrich_movie(movie_id, {"movie_id": movie_id, "title": title}, poster_lookup))
            if len(results) >= 20:
                break
    return results


class SeedsRequest(BaseModel):
    seeds: list[int]
    shuffle: bool = False
    genres: list[str] | None = None
    year_min: int | None = None
    year_max: int | None = None


@app.post("/recommendations")
def recommendations(request: SeedsRequest):
    if not request.seeds or len(request.seeds) > 5:
        return JSONResponse(status_code=400, content={"detail": "seeds must be 1 to 5 items"})

    try:
        result = seed_ranker.rank(
            request.seeds,
            request.shuffle,
            catalog,
            genres=request.genres,
            year_min=request.year_min,
            year_max=request.year_max,
        )
    except seed_ranker.InvalidSeedsError:
        return JSONResponse(status_code=400, content={"detail": "no valid seeds"})
    except seed_ranker.ContentUnavailableError:
        return JSONResponse(status_code=503, content={"content_unavailable": True})

    if not result.items:
        return {"items": [], "seed_movies": [], "anchor_source": "seed", "model_version": model_version}

    return {
        "items": [
            movie_payload(item.movie_id, title=item.title, score=item.fusion_score)
            for item in result.items
        ],
        "seed_movies": [movie_payload(mid) for mid in result.seed_movie_ids],
        "anchor_source": "seed",
        "model_version": model_version,
    }


@app.post("/explanations")
def explanations(request: SeedsRequest):
    if not request.seeds or len(request.seeds) > 5:
        return JSONResponse(status_code=400, content={"detail": "seeds must be 1 to 5 items"})

    try:
        result = seed_ranker.rank(
            request.seeds,
            request.shuffle,
            catalog,
            genres=request.genres,
            year_min=request.year_min,
            year_max=request.year_max,
        )
    except seed_ranker.InvalidSeedsError:
        return JSONResponse(status_code=400, content={"detail": "no valid seeds"})
    except seed_ranker.ContentUnavailableError:
        return JSONResponse(status_code=503, content={"content_unavailable": True})

    topk = [
        {
            "movie_id": item.movie_id,
            "title": item.title,
            "content": item.content_score,
            "final": item.fusion_score,
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
