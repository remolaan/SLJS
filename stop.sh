#!/usr/bin/env bash
# =============================================================
#  AI Judge — stop.sh
#  Stops the backend (FastAPI :8000) and frontend (Vite :5173)
#  and closes the app ports in firewalld (if sudo).
#
#  Usage:
#    ./stop.sh            # normal (kill processes only)
#    sudo ./stop.sh       # also closes ports 8000 & 5173 in firewalld
# =============================================================
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=5173
PID_FILE="$ROOT/.run.pids"

echo "🛑 AI Judge — stopping..."

# --- kill by pid file first ---------------------------------------------------
if [ -f "$PID_FILE" ]; then
  echo "⏹️  Stopping processes from pid file"
  while IFS= read -r pid; do
    kill "$pid" 2>/dev/null && echo "   killed $pid" || true
  done < "$PID_FILE"
  rm -f "$PID_FILE"
fi

# --- kill any remaining matching processes ------------------------------------
pkill -f "uvicorn app.main:app" 2>/dev/null && echo "   Backend stopped" || echo "   Backend not running"
pkill -f "vite" 2>/dev/null && echo "   Frontend stopped" || echo "   Frontend not running"
sleep 2

# force kill if still alive
if pgrep -f "uvicorn app.main:app" >/dev/null || pgrep -f "vite" >/dev/null; then
  echo "⚠️  Some processes remain — force killing..."
  pkill -9 -f "uvicorn app.main:app" 2>/dev/null || true
  pkill -9 -f "vite" 2>/dev/null || true
  sleep 1
fi

# --- close the app ports (only as root & firewalld active) ----------------------
if [ "$(id -u)" -eq 0 ] && command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
  echo "🔒 firewalld is active — closing ports ${BACKEND_PORT}/tcp and ${FRONTEND_PORT}/tcp"
  firewall-cmd --permanent --remove-port=${BACKEND_PORT}/tcp >/dev/null 2>&1 || true
  firewall-cmd --permanent --remove-port=${FRONTEND_PORT}/tcp >/dev/null 2>&1 || true
  firewall-cmd --reload >/dev/null 2>&1 || true
  echo "   Port ${BACKEND_PORT}: $(firewall-cmd --query-port=${BACKEND_PORT}/tcp 2>/dev/null)"
  echo "   Port ${FRONTEND_PORT}: $(firewall-cmd --query-port=${FRONTEND_PORT}/tcp 2>/dev/null)"
else
  echo "ℹ️  Skipping firewall changes (not root / firewalld inactive)."
fi

echo "✅ All stopped."