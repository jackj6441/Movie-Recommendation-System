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
