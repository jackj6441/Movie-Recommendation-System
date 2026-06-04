# API benchmarks

```bash
python benchmarks/benchmark_api.py --base-url http://localhost:8000 --requests 20 --environment local
```

Portfolio sync (updates `services/reco-api/evidence/system_evidence.json`):

```bash
python benchmarks/benchmark_api.py --base-url http://localhost:8000 --requests 20 --sync-evidence
```

Details: `docs/benchmarking.md`.
