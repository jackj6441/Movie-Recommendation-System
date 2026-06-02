import json
import subprocess
import sys
from pathlib import Path


def _dataset_dir() -> str:
    """Prefer the committed ml-32m sample when present, else ml-latest-small.

    The sample is generated during the offline 32M pipeline and committed
    alongside the 32M-based artifacts so these smoke tests run on a dataset in
    the same id space as the committed model/embeddings.
    """
    sample = Path("data/ml-32m-sample")
    if (sample / "ratings.csv").exists() and (sample / "movies.csv").exists():
        return str(sample)
    return "ml-latest-small"


_RATINGS_CSV = f"{_dataset_dir()}/ratings.csv"
_MOVIES_CSV = f"{_dataset_dir()}/movies.csv"


def test_build_report_writes_json_and_markdown(tmp_path):
    model_metrics = tmp_path / "model_metrics.json"
    model_metrics.write_text(
        json.dumps({"rmse": 0.91, "sample_count": 25}),
        encoding="utf-8",
    )
    retrieval_metrics = tmp_path / "retrieval_metrics.json"
    retrieval_metrics.write_text(
        json.dumps(
            {
                "recall_at_k": 0.2,
                "ndcg_at_k": 0.1,
                "recommendation_coverage": 0.3,
                "topk_diversity": 0.4,
                "popularity_baseline_recall_at_k": 0.05,
                "content_baseline_recall_at_k": 0.2,
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "evaluation/build_report.py",
            "--model-metrics",
            str(model_metrics),
            "--retrieval-metrics",
            str(retrieval_metrics),
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
    assert report["model_metrics"]["rmse"] == 0.91
    assert report["retrieval_metrics"]["recall_at_k"] == 0.2

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# Evaluation Report" in markdown
    assert "RMSE" in markdown
    assert "Recall@K" in markdown


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
            _RATINGS_CSV,
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


def test_eval_retrieval_writes_ranking_and_baseline_metrics(tmp_path):
    output_path = tmp_path / "retrieval_metrics.json"
    result = subprocess.run(
        [
            sys.executable,
            "evaluation/eval_retrieval.py",
            "--ratings",
            _RATINGS_CSV,
            "--movies",
            _MOVIES_CSV,
            "--content-embeddings",
            "services/reco-api/models/content_embeddings.npz",
            "--content-index",
            "services/reco-api/models/content_index.json",
            "--max-users",
            "5",
            "--k",
            "10",
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    metrics = json.loads(output_path.read_text(encoding="utf-8"))
    assert metrics["user_count"] == 5
    assert 0 <= metrics["recall_at_k"] <= 1
    assert 0 <= metrics["ndcg_at_k"] <= 1
    assert 0 <= metrics["recommendation_coverage"] <= 1
    assert "topk_diversity" in metrics
    assert "popularity_baseline_recall_at_k" in metrics
    assert "content_baseline_recall_at_k" in metrics


def test_model_card_documents_evaluation_context():
    model_card = Path("docs/model-card.md")
    assert model_card.exists()

    content = model_card.read_text(encoding="utf-8").lower()
    for section in [
        "dataset",
        "split",
        "metrics",
        "artifacts",
        "limitations",
        "risks",
    ]:
        assert section in content
