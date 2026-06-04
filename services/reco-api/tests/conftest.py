import importlib
import sys
from pathlib import Path

import pytest

_APP_MODULES = [
    "app.main",
    "app.content",
    "app.rag",
    "app.seed_ranker",
    "app.metrics",
    "app.posters",
]


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def api_root(repo_root: Path) -> Path:
    return repo_root / "services" / "reco-api"


def _configure_test_env(monkeypatch, repo_root: Path, api_root: Path, **extra: str) -> None:
    monkeypatch.setenv("MOVIES_CSV_PATH", str(repo_root / "ml-latest-small" / "movies.csv"))
    monkeypatch.setenv("RATINGS_CSV_PATH", str(repo_root / "ml-latest-small" / "ratings.csv"))
    monkeypatch.setenv(
        "SERVING_STATS_PATH",
        str(repo_root / "ml-latest-small" / "__no_serving_stats__.json"),
    )
    monkeypatch.setenv("CONTENT_EMBEDDINGS_PATH", str(api_root / "models" / "content_embeddings.npz"))
    monkeypatch.setenv("CONTENT_INDEX_PATH", str(api_root / "models" / "content_index.json"))
    for key, value in extra.items():
        monkeypatch.setenv(key, value)


def _reload_app(api_root: Path):
    sys.path.insert(0, str(api_root))
    for module_name in _APP_MODULES:
        sys.modules.pop(module_name, None)
    return importlib.import_module("app.main").app


@pytest.fixture
def load_app(monkeypatch, repo_root: Path, api_root: Path):
    _configure_test_env(monkeypatch, repo_root, api_root)
    return _reload_app(api_root)


@pytest.fixture
def poster_load_app(monkeypatch, repo_root: Path, api_root: Path):
    fixtures = api_root / "tests" / "fixtures"
    _configure_test_env(
        monkeypatch,
        repo_root,
        api_root,
        POSTER_URLS_PATH=str(fixtures / "poster_urls.sample.json"),
    )
    return _reload_app(api_root)
