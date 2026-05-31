import json
import subprocess
import sys


def test_build_report_writes_json_and_markdown(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "evaluation/build_report.py",
            "--output-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    json_path = tmp_path / "eval_report.json"
    markdown_path = tmp_path / "eval_report.md"
    assert json_path.exists()
    assert markdown_path.exists()

    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["project"] == "movie-recommendation-system"
    assert "generated_at" in report

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# Evaluation Report" in markdown


def test_eval_model_writes_rmse_metrics(tmp_path):
    output_path = tmp_path / "model_metrics.json"
    result = subprocess.run(
        [
            sys.executable,
            "evaluation/eval_model.py",
            "--model",
            "services/reco-api/models/ncf.onnx",
            "--metadata",
            "services/reco-api/models/metadata.json",
            "--ratings",
            "ml-latest-small/ratings.csv",
            "--max-samples",
            "25",
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    metrics = json.loads(output_path.read_text(encoding="utf-8"))
    assert metrics["artifact"] == "services/reco-api/models/ncf.onnx"
    assert metrics["sample_count"] == 25
    assert metrics["rmse"] > 0
