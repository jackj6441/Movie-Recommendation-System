#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Kill all child processes on Ctrl+C or script exit
cleanup() {
  echo ""
  echo "Shutting down..."
  kill 0
}
trap cleanup INT TERM EXIT

# Start backend
(
  cd "$ROOT/services/reco-api"
  set -a && source .env && set +a
  MOVIES_CSV_PATH="$ROOT/ml-latest-small/movies.csv" \
  RATINGS_CSV_PATH="$ROOT/ml-latest-small/ratings.csv" \
  ONNX_MODEL_PATH="$ROOT/services/reco-api/models/ncf.onnx" \
  METADATA_PATH="$ROOT/services/reco-api/models/metadata.json" \
  CONTENT_EMBEDDINGS_PATH="$ROOT/services/reco-api/models/content_embeddings.npz" \
  CONTENT_INDEX_PATH="$ROOT/services/reco-api/models/content_index.json" \
  REDIS_URL=redis://127.0.0.1:6379/0 \
  "$ROOT/.venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) &

# Release port 5173 if a previous session left it occupied
lsof -ti :5173 | xargs kill -9 2>/dev/null || true

# Start frontend
(
  cd "$ROOT/web"
  npm run dev
) &

wait
