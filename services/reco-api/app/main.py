import csv
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from app import content, metrics, movie_details, posters, seed_ranker
from app import rag_chat_sse as rag_chat_service
from app.artifact_bundle import get_default_bundle
from app.rag_session import GLOBAL_SESSION_STORE
from app.rag_resolve import MAX_SEEDS
from app.runtime_catalog import load_runtime_catalog_from_env

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
poster_urls_path = os.getenv("POSTER_URLS_PATH", "models/poster_urls.json")
poster_meta_path = os.getenv("POSTER_META_PATH", "models/poster_meta.json")
movie_details_path = os.getenv("MOVIE_DETAILS_PATH", "models/movie_details.json")
movie_details_meta_path = os.getenv("MOVIE_DETAILS_META_PATH", "models/movie_details_meta.json")
default_system_evidence_path = Path(__file__).resolve().parents[1] / "evidence" / "system_evidence.json"
system_evidence_path = os.getenv("SYSTEM_EVIDENCE_PATH", str(default_system_evidence_path))

content_ok = False
try:
    get_default_bundle()
    content_ok = get_default_bundle().health()["content_ok"]
except Exception:
    print("Warning: content embeddings unavailable at startup")

runtime_catalog = load_runtime_catalog_from_env()

poster_lookup = posters.load_poster_lookup(poster_urls_path)
poster_meta = posters.load_poster_meta(poster_meta_path)
details_lookup = movie_details.load_details_lookup(movie_details_path)
details_meta = movie_details.load_details_meta(movie_details_meta_path)
if not poster_lookup and os.path.exists(poster_urls_path):
    print(f"Warning: poster lookup at {poster_urls_path} is empty or unreadable")
elif not os.path.exists(poster_urls_path):
    print(f"Warning: poster lookup not found at {poster_urls_path}")
if not details_lookup and os.path.exists(movie_details_path):
    print(f"Warning: movie details at {movie_details_path} is empty or unreadable")
elif not os.path.exists(movie_details_path):
    print(f"Warning: movie details not found at {movie_details_path}")


def get_title(movie_id: int) -> str:
    return runtime_catalog.get_title(movie_id)


def movie_payload(movie_id: int, **fields) -> dict:
    return runtime_catalog.movie_payload(movie_id, poster_lookup, details_lookup, **fields)


def serving_status() -> dict:
    status = {
        "status": "ok",
        "content_ok": content_ok,
        "model_version": model_version,
        "ranking_mode": seed_ranker.active_ranking_mode_label(),
    }
    status.update(runtime_catalog.health_fields())
    status.update(get_default_bundle().health())
    status.update(
        posters.poster_health_fields(poster_lookup, poster_meta, len(runtime_catalog.movie_titles))
    )
    status.update(
        movie_details.details_health_fields(
            details_lookup, details_meta, len(runtime_catalog.movie_titles)
        )
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
    return [{"name": genre} for genre in sorted(runtime_catalog.known_genres)]


@app.get("/genres/{genre}/seeds")
def genre_seeds(genre: str, limit: int = 20):
    movie_ids = runtime_catalog.genre_seed_ids(genre, limit)
    return {"seeds": [movie_payload(movie_id) for movie_id in movie_ids]}


@app.get("/movies/search")
def movie_search(q: str = ""):
    return runtime_catalog.search_payloads(q, poster_lookup, details_lookup)


class SeedsRequest(BaseModel):
    seeds: list[int]
    shuffle: bool = False
    genres: list[str] | None = None
    year_min: int | None = None
    year_max: int | None = None


class RagChatRequest(BaseModel):
    session_id: str | None = None
    message: str = ""
    genres: list[str] | None = None
    seed_movie_ids: list[int] | None = None
    seed_update_mode: str = "append"
    reset_context: bool = False
    clear_year_bounds: bool = False
    year_min: int | None = None
    year_max: int | None = None
    disambiguation_genre: str | None = None
    shuffle: bool = False


@app.post("/recommendations")
def recommendations(request: SeedsRequest):
    if not request.seeds or len(request.seeds) > MAX_SEEDS:
        return JSONResponse(
            status_code=400,
            content={"detail": f"seeds must be 1 to {MAX_SEEDS} items"},
        )

    try:
        result = seed_ranker.rank_seed_set(
            seed_ranker.RankRequest(
                seed_movie_ids=request.seeds,
                catalog=runtime_catalog,
                filters=seed_ranker.RankFilters(
                    genres=request.genres,
                    year_min=request.year_min,
                    year_max=request.year_max,
                ),
                shuffle=request.shuffle,
            )
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
    if not request.seeds or len(request.seeds) > MAX_SEEDS:
        return JSONResponse(
            status_code=400,
            content={"detail": f"seeds must be 1 to {MAX_SEEDS} items"},
        )

    try:
        result = seed_ranker.rank_seed_set(
            seed_ranker.RankRequest(
                seed_movie_ids=request.seeds,
                catalog=runtime_catalog,
                filters=seed_ranker.RankFilters(
                    genres=request.genres,
                    year_min=request.year_min,
                    year_max=request.year_max,
                ),
                shuffle=request.shuffle,
            )
        )
    except seed_ranker.InvalidSeedsError:
        return JSONResponse(status_code=400, content={"detail": "no valid seeds"})
    except seed_ranker.ContentUnavailableError:
        return JSONResponse(status_code=503, content={"content_unavailable": True})

    topk = result.explanation_topk()
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


@app.post("/rag/chat")
def rag_chat(request: RagChatRequest):
    stream = rag_chat_service.run_chat_turn_sse(
        session_store=GLOBAL_SESSION_STORE,
        catalog=runtime_catalog,
        model_version=os.getenv("MODEL_VERSION", model_version),
        movie_payload_fn=movie_payload,
        message=request.message,
        genres=request.genres,
        session_id=request.session_id,
        shuffle=request.shuffle,
        seed_movie_ids=request.seed_movie_ids,
        seed_update_mode=request.seed_update_mode,
        reset_context=request.reset_context,
        clear_year_bounds=request.clear_year_bounds,
        year_min=request.year_min,
        year_max=request.year_max,
        disambiguation_genre=request.disambiguation_genre,
    )
    return StreamingResponse(stream, media_type="text/event-stream")


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
