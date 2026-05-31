import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build evaluation report artifacts")
    parser.add_argument("--output-dir", default="evaluation/results")
    return parser.parse_args()


def build_report() -> dict:
    return {
        "project": "movie-recommendation-system",
        "generated_at": datetime.now(UTC).isoformat(),
        "metrics": {},
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
            "No metric inputs were provided yet.",
            "",
        ]
    )


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_report()
    (output_dir / "eval_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "eval_report.md").write_text(write_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
