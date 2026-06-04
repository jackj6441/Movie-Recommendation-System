import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build evaluation report artifacts")
    parser.add_argument(
        "--retrieval-metrics",
        default="evaluation/results/retrieval_metrics.json",
    )
    parser.add_argument(
        "--fusion-metrics",
        default="evaluation/results/fusion_metrics.json",
    )
    parser.add_argument(
        "--fusion-tune",
        default="evaluation/results/fusion_tune.json",
    )
    parser.add_argument("--output-dir", default="evaluation/results")
    return parser.parse_args()


def load_json(path: str | None) -> dict:
    if not path:
        return {}
    if not Path(path).exists():
        return {}
    with open(path, encoding="utf-8") as metrics_file:
        return json.load(metrics_file)


def build_report(
    retrieval_metrics: dict | None = None,
    fusion_metrics: dict | None = None,
    fusion_tune: dict | None = None,
) -> dict:
    return {
        "project": "movie-recommendation-system",
        "generated_at": datetime.now(UTC).isoformat(),
        "retrieval_metrics": retrieval_metrics or {},
        "fusion_metrics": fusion_metrics or {},
        "fusion_tune": fusion_tune or {},
    }


def write_markdown(report: dict) -> str:
    fusion = report.get("fusion_metrics", {})
    tune = report.get("fusion_tune", {})
    lines = [
        "# Evaluation Report",
        "",
        f"- Project: `{report['project']}`",
        f"- Generated at: `{report['generated_at']}`",
        "",
        "## Content-only retrieval metrics",
        "",
        f"- Recall@K: `{report['retrieval_metrics'].get('recall_at_k', 'n/a')}`",
        f"- NDCG@K: `{report['retrieval_metrics'].get('ndcg_at_k', 'n/a')}`",
        f"- Recommendation coverage: `{report['retrieval_metrics'].get('recommendation_coverage', 'n/a')}`",
        f"- Top-K diversity: `{report['retrieval_metrics'].get('topk_diversity', 'n/a')}`",
        f"- Popularity baseline Recall@K: `{report['retrieval_metrics'].get('popularity_baseline_recall_at_k', 'n/a')}`",
        "",
        "## Phase 1 fusion metrics",
        "",
        f"- Recall@10: `{fusion.get('recall_at_10', 'n/a')}`",
        f"- Recall@24: `{fusion.get('recall_at_24', 'n/a')}`",
        f"- NDCG@10: `{fusion.get('ndcg_at_10', 'n/a')}`",
        f"- NDCG@24: `{fusion.get('ndcg_at_24', 'n/a')}`",
        f"- Popularity baseline Recall@10: `{fusion.get('popularity_baseline_recall_at_10', 'n/a')}`",
        f"- Fusion weights: `{fusion.get('fusion_weights', tune.get('best_weights', 'n/a'))}`",
        "",
    ]
    if tune:
        lines.extend(
            [
                "## Fusion weight tuning",
                "",
                f"- Objective: `{tune.get('objective', 'n/a')}`",
                f"- Best score: `{tune.get('best_score', 'n/a')}`",
                f"- Best weights: `{tune.get('best_weights', 'n/a')}`",
                f"- Candidates tried: `{tune.get('candidate_count', 'n/a')}`",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_report(
        retrieval_metrics=load_json(args.retrieval_metrics),
        fusion_metrics=load_json(args.fusion_metrics),
        fusion_tune=load_json(args.fusion_tune),
    )
    (output_dir / "eval_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "eval_report.md").write_text(write_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
