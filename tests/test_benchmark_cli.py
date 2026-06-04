import json
import subprocess
import sys
from pathlib import Path


def test_benchmark_cli_writes_json_and_markdown_reports(tmp_path):
    base_url = "mock://local"

    result = subprocess.run(
        [
            sys.executable,
            "benchmarks/benchmark_api.py",
            "--base-url",
            base_url,
            "--requests",
            "2",
            "--output-dir",
            str(tmp_path),
            "--environment",
            "test",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    json_path = tmp_path / "benchmark_report.json"
    markdown_path = tmp_path / "benchmark_report.md"
    assert json_path.exists()
    assert markdown_path.exists()

    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["base_url"] == base_url
    assert report["environment"] == "test"
    assert "timestamp" in report

    endpoints = {endpoint["name"]: endpoint for endpoint in report["endpoints"]}
    assert set(endpoints) == {
        "GET /healthz",
        "GET /metrics",
        "POST /recommendations",
        "POST /explanations",
        "POST /rag/explanations",
    }
    assert report["serving"]["ranking_mode"] == "multi_retriever_fusion"
    for endpoint in endpoints.values():
        assert endpoint["request_count"] == 2
        assert endpoint["success_rate"] == 1.0
        assert endpoint["p50_ms"] >= 0
        assert endpoint["p95_ms"] >= 0
        assert endpoint["p99_ms"] >= 0

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# API Benchmark Report" in markdown
    assert "GET /healthz" in markdown
    assert "POST /rag/explanations" in markdown


def test_benchmark_sync_evidence_merges_latency_and_fusion_metrics(tmp_path):
    evidence_path = tmp_path / "system_evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "system_name": "movie-recommendation-system",
                "evaluation": {"recall_at_k": 0.04},
                "benchmark": {"recommendations_p95_ms": 1.0},
            }
        ),
        encoding="utf-8",
    )
    fusion_metrics = tmp_path / "fusion_metrics.json"
    fusion_metrics.write_text(
        json.dumps(
            {
                "recall_at_10": 0.11,
                "recall_at_24": 0.15,
                "ndcg_at_10": 0.05,
                "ndcg_at_24": 0.07,
                "user_count": 50,
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "benchmarks/benchmark_api.py",
            "--base-url",
            "mock://local",
            "--requests",
            "2",
            "--output-dir",
            str(tmp_path / "bench"),
            "--sync-evidence",
            "--evidence-path",
            str(evidence_path),
            "--fusion-metrics",
            str(fusion_metrics),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["benchmark"]["recommendations_p95_ms"] >= 0
    assert evidence["benchmark"]["ranking_mode"] == "multi_retriever_fusion"
    assert evidence["evaluation"]["recall_at_10"] == 0.11
    assert evidence["evaluation"]["ndcg_at_24"] == 0.07
    assert "generated_at" in evidence


def test_benchmark_docs_explain_command_and_artifacts():
    docs = Path("docs/benchmarking.md")
    assert docs.exists()

    content = docs.read_text(encoding="utf-8")
    assert "python benchmarks/benchmark_api.py" in content
    assert "--base-url" in content
    assert "benchmark_report.json" in content
    assert "benchmark_report.md" in content
    assert "p50" in content
    assert "p95" in content
    assert "p99" in content
    assert "--sync-evidence" in content
    assert "multi_retriever_fusion" in content or "fusion" in content.lower()


def test_local_benchmark_report_artifact_is_published():
    report_path = Path("benchmarks/results/benchmark_report.json")
    markdown_path = Path("benchmarks/results/benchmark_report.md")
    assert report_path.exists()
    assert markdown_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["environment"] == "local"
    assert report["request_count_per_endpoint"] > 0
    assert {endpoint["name"] for endpoint in report["endpoints"]} == {
        "GET /healthz",
        "GET /metrics",
        "POST /recommendations",
        "POST /explanations",
        "POST /rag/explanations",
    }
    assert report.get("serving", {}).get("ranking_mode") == "multi_retriever_fusion"
