from pathlib import Path


def test_ci_workflow_defines_required_quality_gates():
    workflow = Path(".github/workflows/ci.yml")
    assert workflow.exists()

    content = workflow.read_text(encoding="utf-8")
    for expected in [
        "backend-tests",
        "frontend-tests",
        "frontend-build",
        "backend-docker-build",
        "frontend-docker-build",
        "RAG_PROVIDER: mock",
        "python -m pytest tests services/reco-api/tests -q",
        "npm test -- --run",
        "npm run build",
        "docker build -t movie-reco-api-ci services/reco-api",
        "docker build -t movie-reco-web-ci web",
    ]:
        assert expected in content
