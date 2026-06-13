#!/usr/bin/env bash
# start.sh — Kill any stale servers, then start FastAPI backend + Vite frontend

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT_DIR/.venv/bin"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   🔐  Differentially Private RAG Chatbot             ║"
echo "║   Backend → http://localhost:8000                    ║"
echo "║   Frontend → http://localhost:3000                   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Kill anything already on these ports ─────────────────────────────────────
echo "🧹 Freeing ports 8000 and 3000…"
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 3000/tcp 2>/dev/null || true
sleep 1
echo "   Done."
echo ""

# ── 1. Start FastAPI backend ─────────────────────────────────────────────────
echo "▶ Starting FastAPI backend on port 8000…"
PYTHONPATH="$PROJECT_DIR/src" \
  "$VENV/uvicorn" backend.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir "$PROJECT_DIR/src" \
  --reload-dir "$PROJECT_DIR/backend" &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Wait until backend is accepting connections
echo "  Waiting for backend to be ready…"
for i in $(seq 1 20); do
  if curl -sf http://localhost:8000/api/status >/dev/null 2>&1; then
    echo "  ✅ Backend ready!"
    break
  fi
  sleep 0.5
done

echo ""

# ── 2. Start Node.js frontend ────────────────────────────────────────────────
echo "▶ Starting Node.js frontend on port 3000…"
cd "$PROJECT_DIR/frontend"

# Install dependencies if node_modules is missing
if [ ! -d node_modules ]; then
  echo "  Installing npm packages…"
  npm install
fi

npm run dev &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"
sleep 2

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✅ Both servers are running!"
echo "  🌐 Open → http://localhost:3000"
echo "════════════════════════════════════════════════════════"
echo ""
echo "  Press Ctrl+C to stop both servers."
echo ""

# Graceful cleanup on Ctrl+C / SIGTERM
cleanup() {
  echo ""
  echo "🛑 Stopping servers…"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  fuser -k 8000/tcp 2>/dev/null || true
  fuser -k 3000/tcp 2>/dev/null || true
  echo "   Stopped. Goodbye!"
  exit 0
}
trap cleanup SIGINT SIGTERM

wait
