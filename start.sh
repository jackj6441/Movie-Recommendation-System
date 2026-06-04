#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  echo ""
  echo "Shutting down..."
  kill 0
}
trap cleanup INT TERM EXIT

(
  cd "$ROOT/services/reco-api"
  if [[ -f "$ROOT/.env" ]]; then
    set -a && source "$ROOT/.env" && set +a
  fi
  MOVIES_CSV_PATH="$ROOT/ml-latest-small/movies.csv" \
  RATINGS_CSV_PATH="$ROOT/ml-latest-small/ratings.csv" \
  CONTENT_EMBEDDINGS_PATH="$ROOT/services/reco-api/models/content_embeddings.npz" \
  CONTENT_INDEX_PATH="$ROOT/services/reco-api/models/content_index.json" \
  "$ROOT/.venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) &

lsof -ti :5173 | xargs kill -9 2>/dev/null || true

(
  cd "$ROOT/web"
  npm run dev
) &

wait
