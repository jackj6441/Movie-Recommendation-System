import argparse
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib import error, request


ENDPOINTS = [
    {
        "name": "GET /healthz",
        "method": "GET",
        "path": "/healthz",
        "body": None,
    },
    {
        "name": "POST /recommendations",
        "method": "POST",
        "path": "/recommendations",
        "body": {"seeds": [1, 2, 3], "shuffle": False},
    },
    {
        "name": "POST /explanations",
        "method": "POST",
        "path": "/explanations",
        "body": {"seeds": [1, 2, 3], "shuffle": False},
    },
    {
        "name": "POST /rag/explanations",
        "method": "POST",
        "path": "/rag/explanations",
        "body": {"seeds": [1, 2, 3], "shuffle": False},
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark recommendation API endpoints")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--output-dir", default="benchmarks/results")
    parser.add_argument("--environment", default="local")
    parser.add_argument("--timeout", type=float, default=10.0)
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


def benchmark_endpoint(base_url: str, endpoint: dict, request_count: int, timeout: float) -> dict:
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
        "request_count": request_count,
        "success_count": successes,
        "success_rate": successes / request_count if request_count else 0.0,
        "p50_ms": percentile(latencies, 0.50),
        "p95_ms": percentile(latencies, 0.95),
        "p99_ms": percentile(latencies, 0.99),
        "mean_ms": statistics.fmean(latencies) if latencies else 0.0,
    }


def build_report(args: argparse.Namespace) -> dict:
    return {
        "base_url": args.base_url,
        "environment": args.environment,
        "timestamp": datetime.now(UTC).isoformat(),
        "request_count_per_endpoint": args.requests,
        "endpoints": [
            benchmark_endpoint(args.base_url, endpoint, args.requests, args.timeout)
            for endpoint in ENDPOINTS
        ],
    }


def write_markdown(report: dict) -> str:
    lines = [
        "# API Benchmark Report",
        "",
        f"- Base URL: `{report['base_url']}`",
        f"- Environment: `{report['environment']}`",
        f"- Timestamp: `{report['timestamp']}`",
        f"- Requests per endpoint: `{report['request_count_per_endpoint']}`",
        "",
        "| Endpoint | Success rate | p50 ms | p95 ms | p99 ms | Requests |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for endpoint in report["endpoints"]:
        lines.append(
            "| {name} | {success_rate:.2f} | {p50_ms:.3f} | {p95_ms:.3f} | {p99_ms:.3f} | {request_count} |".format(
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
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
