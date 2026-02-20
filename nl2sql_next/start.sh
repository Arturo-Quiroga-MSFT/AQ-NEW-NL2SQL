#!/usr/bin/env bash
# Start NL2SQL — kills existing processes on ports 8000/5173, then launches
# FastAPI backend + React/Vite frontend.
#
# Usage:  cd nl2sql_next && ./start.sh

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/../.venv/bin/activate"

echo "=== NL2SQL Start ==="

# Kill anything on ports 8000 and 5173
for PORT in 8000 5173; do
  PID=$(lsof -ti tcp:$PORT 2>/dev/null || true)
  if [ -n "$PID" ]; then
    echo "Killing process on port $PORT (PID $PID)"
    kill -9 $PID 2>/dev/null || true
    sleep 0.5
  fi
done

# Start FastAPI backend
echo "Starting FastAPI backend on :8000 …"
source "$VENV"
cd "$DIR"
uvicorn api:app --reload --port 8000 &
BACKEND_PID=$!

# Start Vite frontend
echo "Starting Vite frontend on :5173 …"
cd "$DIR/frontend"
npm run dev -- --port 5173 &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000  (PID $BACKEND_PID)"
echo "Frontend: http://localhost:5173  (PID $FRONTEND_PID)"
echo ""
echo "Press Ctrl+C to stop both."

# Trap Ctrl+C to kill both
trap "echo 'Stopping…'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
