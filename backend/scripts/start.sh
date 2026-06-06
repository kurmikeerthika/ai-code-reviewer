#!/bin/bash
# scripts/start.sh
# Container startup script.
#
# Runs before the FastAPI server starts to:
# 1. Validate required environment variables
# 2. Create necessary directories
# 3. Start the Uvicorn server with the right settings

set -e  # Exit immediately if any command fails

echo "=============================================="
echo "  AI Code Reviewer — Starting Up"
echo "=============================================="

# ── Validate required environment variables ────
echo "→ Checking environment variables..."

# if [ -z "$OPENAI_API_KEY" ]; then
#     echo "ERROR: OPENAI_API_KEY is not set!"
#     echo "  Add it to your .env file or Docker environment."
#     exit 1
# fi

# echo "  ✓ OPENAI_API_KEY is set"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "  ⚠ WARNING: GITHUB_TOKEN is not set."
    echo "    GitHub PR review will not be available."
else
    echo "  ✓ GITHUB_TOKEN is set"
fi

# ── Create runtime directories ─────────────────
echo "→ Creating runtime directories..."
mkdir -p /app/chroma_db /app/uploads /app/logs
echo "  ✓ Directories ready"

# ── Set defaults for optional variables ────────
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-1}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "→ Configuration:"
echo "  Host:      $HOST"
echo "  Port:      $PORT"
echo "  Workers:   $WORKERS"
echo "  Log Level: $LOG_LEVEL"
echo "  Debug:     ${DEBUG:-false}"

echo "=============================================="
echo "  Starting Uvicorn server..."
echo "=============================================="

# Start the FastAPI server
# --host:         listen on all interfaces
# --port:         from environment variable
# --workers:      number of worker processes
# --log-level:    logging verbosity
# --access-log:   log every request
# NO --reload:    reload is for development only, not production
exec uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL" \
    --access-log