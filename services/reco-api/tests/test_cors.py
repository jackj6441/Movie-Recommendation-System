from fastapi.testclient import TestClient


def test_cors_allows_vite_dev_port_fallback(poster_load_app):
    client = TestClient(poster_load_app)

    response = client.get("/genres", headers={"Origin": "http://localhost:3002"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3002"


def test_cors_allows_configured_ec2_frontend_origin(poster_load_app, monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://34.228.75.214:3000")
    import importlib
    import sys
    from pathlib import Path

    api_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(api_root))
    for module_name in [
        "app.main",
        "app.content",
        "app.rag",
        "app.seed_ranker",
        "app.metrics",
        "app.posters",
        "app.artifacts",
        "app.fusion",
    ]:
        sys.modules.pop(module_name, None)
    app = importlib.import_module("app.main").app
    client = TestClient(app)

    response = client.options(
        "/recommendations",
        headers={
            "Origin": "http://34.228.75.214:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://34.228.75.214:3000"
