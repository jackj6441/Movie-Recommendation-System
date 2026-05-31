from pathlib import Path


def test_ec2_deployment_doc_covers_public_demo_validation():
    doc_path = Path("docs/deployment-ec2.md")
    assert doc_path.exists()

    content = doc_path.read_text(encoding="utf-8")
    for expected in [
        "AWS EC2",
        "Docker Compose",
        "security group",
        "PUBLIC_API_BASE",
        "RAG_PROVIDER=mock",
        "curl http://<ec2-public-ip>:8000/healthz",
        "curl http://<ec2-public-ip>:8000/metrics",
        "docker compose -f infra/docker-compose.yml up --build -d",
        "Do not commit real .env files",
    ]:
        assert expected in content


def test_compose_supports_public_ec2_api_base_and_mock_rag():
    compose = Path("infra/docker-compose.yml").read_text(encoding="utf-8")

    assert "${PUBLIC_API_BASE:-http://localhost:8000}" in compose
    assert "${RAG_PROVIDER:-mock}" in compose
