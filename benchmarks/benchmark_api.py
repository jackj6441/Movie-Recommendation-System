import argparse
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib import error, request

DEFAULT_EVIDENCE_PATH = Path("services/reco-api/evidence/system_evidence.json")
DEFAULT_FUSION_METRICS_PATH = Path("evaluation/results/fusion_metrics.json")

ENDPOINTS = [
    {
        "name": "GET /healthz",
        "method": "GET",
        "path": "/healthz",
        "body": None,
        "timeout_sec": 10.0,
    },
    {
        "name": "GET /metrics",
        "method": "GET",
        "path": "/metrics",
        "body": None,
        "timeout_sec": 10.0,
    },
    {
        "name": "POST /recommendations",
        "method": "POST",
        "path": "/recommendations",
        "body": {"seeds": [1, 2, 3], "shuffle": False},
        "timeout_sec": 60.0,
    },
    {
        "name": "POST /explanations",
        "method": "POST",
        "path": "/explanations",
        "body": {"seeds": [1, 2, 3], "shuffle": False},
        "timeout_sec": 60.0,
    },
    {
        "name": "POST /rag/explanations",
        "method": "POST",
        "path": "/rag/explanations",
        "body": {"seeds": [1, 2, 3], "shuffle": False},
        "timeout_sec": 15.0,
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark recommendation API endpoints")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--output-dir", default="benchmarks/results")
    parser.add_argument("--environment", default="local")
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="override per-endpoint timeouts (seconds) for all endpoints",
    )
    parser.add_argument(
        "--sync-evidence",
        action="store_true",
        help="merge p95 latencies into services/reco-api/evidence/system_evidence.json",
    )
    parser.add_argument(
        "--evidence-path",
        default=str(DEFAULT_EVIDENCE_PATH),
    )
    parser.add_argument(
        "--fusion-metrics",
        default=str(DEFAULT_FUSION_METRICS_PATH),
        help="optional fusion eval JSON to merge into system evidence",
    )
    return parser.parse_args()


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * percent
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def fetch_json(base_url: str, path: str, timeout: float) -> dict | None:
    if base_url.startswith("mock://"):
        return {
            "status": "ok",
            "ranking_mode": "multi_retriever_fusion",
            "fusion_ok": True,
            "svd_ok": False,
            "item_cf_ok": False,
        }
    http_request = request.Request(base_url.rstrip("/") + path, method="GET")
    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            if response.status != 200:
                return None
            return json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def request_once(base_url: str, endpoint: dict, timeout: float) -> tuple[bool, float]:
    started_at = time.perf_counter()
    if base_url.startswith("mock://"):
        return True, (time.perf_counter() - started_at) * 1000

    body = endpoint["body"]
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    http_request = request.Request(
        base_url.rstrip("/") + endpoint["path"],
        data=data,
        headers=headers,
        method=endpoint["method"],
    )
    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            response.read()
            success = 200 <= response.status < 300
    except (error.URLError, TimeoutError):
        success = False
    return success, (time.perf_counter() - started_at) * 1000


def benchmark_endpoint(
    base_url: str,
    endpoint: dict,
    request_count: int,
    timeout_override: float | None,
) -> dict:
    timeout = timeout_override if timeout_override is not None else endpoint["timeout_sec"]
    latencies: list[float] = []
    successes = 0
    for _ in range(request_count):
        success, latency_ms = request_once(base_url, endpoint, timeout)
        latencies.append(latency_ms)
        if success:
            successes += 1

    return {
        "name": endpoint["name"],
        "method": endpoint["method"],
        "path": endpoint["path"],
        "timeout_sec": timeout,
        "request_count": request_count,
        "success_count": successes,
        "success_rate": successes / request_count if request_count else 0.0,
        "p50_ms": percentile(latencies, 0.50),
        "p95_ms": percentile(latencies, 0.95),
        "p99_ms": percentile(latencies, 0.99),
        "mean_ms": statistics.fmean(latencies) if latencies else 0.0,
    }


def endpoint_p95(report: dict, name: str) -> float | None:
    for endpoint in report.get("endpoints", []):
        if endpoint["name"] == name:
            return float(endpoint["p95_ms"])
    return None


def sync_system_evidence(
    report: dict,
    evidence_path: Path,
    fusion_metrics_path: Path,
) -> dict:
    """Patch portfolio evidence with latest benchmark (and optional fusion eval) numbers."""
    if evidence_path.exists():
        with open(evidence_path, encoding="utf-8") as evidence_file:
            evidence = json.load(evidence_file)
    else:
        evidence = {"system_name": "movie-recommendation-system"}

    rec_p95 = endpoint_p95(report, "POST /recommendations")
    explain_p95 = endpoint_p95(report, "POST /explanations")
    rag_p95 = endpoint_p95(report, "POST /rag/explanations")
    benchmark = {
        "environment": report.get("environment"),
        "timestamp": report.get("timestamp"),
        "ranking_mode": (report.get("serving") or {}).get("ranking_mode"),
        "fusion_ok": (report.get("serving") or {}).get("fusion_ok"),
        "svd_ok": (report.get("serving") or {}).get("svd_ok"),
        "item_cf_ok": (report.get("serving") or {}).get("item_cf_ok"),
    }
    if rec_p95 is not None:
        benchmark["recommendations_p95_ms"] = round(rec_p95, 3)
    if explain_p95 is not None:
        benchmark["explanations_p95_ms"] = round(explain_p95, 3)
    if rag_p95 is not None:
        benchmark["rag_explanations_p95_ms"] = round(rag_p95, 3)
    evidence["benchmark"] = benchmark

    if fusion_metrics_path.exists():
        with open(fusion_metrics_path, encoding="utf-8") as metrics_file:
            fusion = json.load(metrics_file)
        evaluation = evidence.setdefault("evaluation", {})
        for key in ("recall_at_10", "recall_at_24", "ndcg_at_10", "ndcg_at_24"):
            if key in fusion:
                evaluation[key] = fusion[key]
        if "user_count" in fusion:
            evaluation["fusion_eval_users"] = fusion["user_count"]

    evidence["generated_at"] = datetime.now(UTC).isoformat()
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence


def build_report(args: argparse.Namespace) -> dict:
    serving = fetch_json(args.base_url, "/healthz", timeout=10.0)
    return {
        "base_url": args.base_url,
        "environment": args.environment,
        "timestamp": datetime.now(UTC).isoformat(),
        "request_count_per_endpoint": args.requests,
        "serving": serving or {},
        "endpoints": [
            benchmark_endpoint(args.base_url, endpoint, args.requests, args.timeout)
            for endpoint in ENDPOINTS
        ],
    }


def write_markdown(report: dict) -> str:
    serving = report.get("serving") or {}
    lines = [
        "# API Benchmark Report",
        "",
        f"- Base URL: `{report['base_url']}`",
        f"- Environment: `{report['environment']}`",
        f"- Timestamp: `{report['timestamp']}`",
        f"- Requests per endpoint: `{report['request_count_per_endpoint']}`",
        f"- Ranking mode: `{serving.get('ranking_mode', 'n/a')}`",
        f"- Fusion ready: `{serving.get('fusion_ok', 'n/a')}` (svd=`{serving.get('svd_ok', 'n/a')}`, item_cf=`{serving.get('item_cf_ok', 'n/a')}`)",
        "",
        "| Endpoint | Success rate | p50 ms | p95 ms | p99 ms | Timeout s | Requests |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for endpoint in report["endpoints"]:
        lines.append(
            "| {name} | {success_rate:.2f} | {p50_ms:.3f} | {p95_ms:.3f} | {p99_ms:.3f} | {timeout_sec:.0f} | {request_count} |".format(
                **endpoint
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    report = build_report(args)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "benchmark_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "benchmark_report.md").write_text(write_markdown(report), encoding="utf-8")

    if args.sync_evidence:
        evidence = sync_system_evidence(
            report,
            Path(args.evidence_path),
            Path(args.fusion_metrics),
        )
        print(
            json.dumps(
                {
                    "synced_evidence": str(args.evidence_path),
                    "benchmark": evidence.get("benchmark", {}),
                },
                sort_keys=True,
            )
        )
    else:
        print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
