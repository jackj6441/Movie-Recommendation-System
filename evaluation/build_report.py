import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build evaluation report artifacts")
    parser.add_argument("--model-metrics", default=None)
    parser.add_argument("--retrieval-metrics", default=None)
    parser.add_argument("--output-dir", default="evaluation/results")
    return parser.parse_args()


def load_json(path: str | None) -> dict:
    if not path:
        return {}
    with open(path, encoding="utf-8") as metrics_file:
        return json.load(metrics_file)


def build_report(model_metrics: dict | None = None, retrieval_metrics: dict | None = None) -> dict:
    return {
        "project": "movie-recommendation-system",
        "generated_at": datetime.now(UTC).isoformat(),
        "model_metrics": model_metrics or {},
        "retrieval_metrics": retrieval_metrics or {},
    }


def write_markdown(report: dict) -> str:
    return "\n".join(
        [
            "# Evaluation Report",
            "",
            f"- Project: `{report['project']}`",
            f"- Generated at: `{report['generated_at']}`",
            "",
            "## Metrics",
            "",
            f"- RMSE: `{report['model_metrics'].get('rmse', 'n/a')}`",
            f"- Model sample count: `{report['model_metrics'].get('sample_count', 'n/a')}`",
            f"- Recall@K: `{report['retrieval_metrics'].get('recall_at_k', 'n/a')}`",
            f"- NDCG@K: `{report['retrieval_metrics'].get('ndcg_at_k', 'n/a')}`",
            f"- Recommendation coverage: `{report['retrieval_metrics'].get('recommendation_coverage', 'n/a')}`",
            f"- Top-K diversity: `{report['retrieval_metrics'].get('topk_diversity', 'n/a')}`",
            f"- Popularity baseline Recall@K: `{report['retrieval_metrics'].get('popularity_baseline_recall_at_k', 'n/a')}`",
            f"- Content baseline Recall@K: `{report['retrieval_metrics'].get('content_baseline_recall_at_k', 'n/a')}`",
            "",
        ]
    )


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_report(
        model_metrics=load_json(args.model_metrics),
        retrieval_metrics=load_json(args.retrieval_metrics),
    )
    (output_dir / "eval_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "eval_report.md").write_text(write_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
