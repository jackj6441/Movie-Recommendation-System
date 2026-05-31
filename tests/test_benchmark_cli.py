import json
import subprocess
import sys


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
        "POST /recommendations",
        "POST /explanations",
        "POST /rag/explanations",
    }
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
