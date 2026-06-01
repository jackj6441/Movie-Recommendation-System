from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_readme_presents_ml_infra_portfolio_story():
    content = read("README.md")

    for expected in [
        "Production-style ML recommendation platform",
        "training -> evaluation -> export -> serving -> caching -> explanation -> monitoring -> deployment",
        "http://34.228.75.214:3000",
        "evaluation/results/eval_report.md",
        "benchmarks/results/benchmark_report.md",
        "GET /healthz",
        "GET /metrics",
        "GET /system/evidence",
        "System Evidence Dashboard",
    ]:
        assert expected in content


def test_runbook_covers_operational_workflows():
    content = read("docs/runbook.md")

    for expected in [
        "Startup",
        "Health Checks",
        "Logs",
        "Restart",
        "Rollback",
        "Secret Handling",
        "Common Failure Modes",
        "docker compose -f infra/docker-compose.yml up --build -d",
        "GET /healthz",
        "GET /metrics",
        "GET /system/evidence",
        "RAG_PROVIDER=mock",
        "CORS_ALLOW_ORIGINS",
    ]:
        assert expected in content


def test_resume_bullets_are_ml_infra_focused_and_copy_ready():
    content = read("docs/resume-bullets.md")

    bullets = [line for line in content.splitlines() if line.startswith("- ")]
    assert 3 <= len(bullets) <= 5

    for expected in [
        "PyTorch Lightning",
        "ONNX Runtime",
        "Redis",
        "FastAPI",
        "React/D3",
        "Docker Compose",
        "Prometheus-style",
        "AWS EC2",
        "mock RAG",
        "System Evidence Dashboard",
    ]:
        assert expected in content


def test_portfolio_docs_state_public_rag_and_model_truth():
    combined = "\n".join(
        read(path)
        for path in [
            "README.md",
            "docs/runbook.md",
            "docs/resume-bullets.md",
        ]
    )

    for expected in [
        "RAG_PROVIDER=mock",
        "Do not commit",
        "Seed Set recommendations driven by Content Signal",
        "NCF / ONNX model remains",
        "product ranking",
    ]:
        assert expected in combined
