#!/usr/bin/env bash
# =============================================================
#  AI Judge — start.sh
#  Boots the backend (FastAPI :8000) and frontend (Vite :5173).
#  Optionally opens the ports in firewalld (only if you're sudo).
#
#  Usage:
#    ./start.sh            # normal (no firewall changes)
#    sudo ./start.sh       # also opens ports 8000 & 5173 in firewalld
# =============================================================
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=5173

BACKEND_LOG="$ROOT/backend.log"
FRONTEND_LOG="$ROOT/frontend.log"
PID_FILE="$ROOT/.run.pids"

echo "🚀 AI Judge — starting..."

# --- firewall (only when running as root & firewalld exists) --------------
if [ "$(id -u)" -eq 0 ] && command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
  echo "🔓 firewalld is active — opening ports ${BACKEND_PORT}/tcp and ${FRONTEND_PORT}/tcp"
  firewall-cmd --permanent --add-port=${BACKEND_PORT}/tcp >/dev/null 2>&1 || true
  firewall-cmd --permanent --add-port=${FRONTEND_PORT}/tcp >/dev/null 2>&1 || true
  firewall-cmd --reload >/dev/null 2>&1 || true
  echo "   Port ${BACKEND_PORT}: $(firewall-cmd --query-port=${BACKEND_PORT}/tcp 2>/dev/null)"
  echo "   Port ${FRONTEND_PORT}: $(firewall-cmd --query-port=${FRONTEND_PORT}/tcp 2>/dev/null)"
else
  echo "ℹ️  Skipping firewall changes (not root / firewalld inactive)."
fi

# --- stop anything already running -----------------------------------------
echo "⏹️  Stopping any previous instances"
[ -f "$PID_FILE" ] && while IFS= read -r pid; do
  kill "$pid" 2>/dev/null || true
done < "$PID_FILE"
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 2
rm -f "$PID_FILE"

# When running under sudo, drop privileges back to the invoking user so the
# app files/logs are not created as root (avoids permission headaches later).
RUN_USER="${SUDO_USER:-$USER}"
if [ "$(id -u)" -eq 0 ] && [ -n "$RUN_USER" ] && [ "$RUN_USER" != "root" ]; then
  RUN_AS="su -s /bin/bash $RUN_USER -c"
  echo "👤 Running app processes as user: $RUN_USER"
else
  RUN_AS="bash -c"
fi

# --- backend ---------------------------------------------------------------
echo "🖥️  Starting backend (FastAPI on :${BACKEND_PORT})"
if [ ! -d "$BACKEND/.venv" ]; then
  echo "   ❌ venv not found at $BACKEND/.venv — run backend setup first."
  echo "      cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi
$RUN_AS "cd '$BACKEND' && setsid nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT} > '$BACKEND_LOG' 2>&1 & echo \$! >> '$PID_FILE'"
echo "   Backend PID recorded -> log: $BACKEND_LOG"

# --- frontend ---------------------------------------------------------------
echo "🎨  Starting frontend (Vite on :${FRONTEND_PORT})"

# Resolve node/npm. They live under nvm and are not on the PATH in the
# detached subshell, so find them explicitly. Under sudo $HOME becomes
# /root, so also check the invoking user's real home (/home/*).
NPM="$(command -v npm 2>/dev/null || true)"
if [ -z "$NPM" ]; then
  for base in "$HOME/.nvm" "$(getent passwd "${SUDO_USER:-$USER}" 2>/dev/null | cut -d: -f6)/.nvm" /home/*/.nvm; do
    for d in "$base"/versions/node/*/bin; do
      if [ -x "$d/npm" ]; then NPM="$d/npm"; break 2; fi
    done
  done
fi
if [ -z "$NPM" ] || [ ! -x "$NPM" ]; then
  echo "   ❌ npm not found. Install Node (e.g. via nvm)."
  exit 1
fi
NODE_BIN="$(dirname "$NPM")"
export PATH="$NODE_BIN:$PATH"

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "   Installing frontend deps (first run)..."
  $RUN_AS "cd '$FRONTEND' && '$NPM' install"
fi
$RUN_AS "cd '$FRONTEND' && setsid nohup '$NPM' run dev -- --host 0.0.0.0 --port ${FRONTEND_PORT} > '$FRONTEND_LOG' 2>&1 & echo \$! >> '$PID_FILE'"
echo "   Frontend PID recorded (npm=$NPM) -> log: $FRONTEND_LOG"

# --- wait + health check -----------------------------------------------------
echo "⏳ Waiting for services to be ready..."
for i in $(seq 1 20); do
  curl -sf "http://localhost:${BACKEND_PORT}/api/health" >/dev/null 2>&1 && break
  sleep 1
done
for i in $(seq 1 20); do
  curl -sf "http://localhost:${FRONTEND_PORT}/" >/dev/null 2>&1 && break
  sleep 1
done

if curl -sf "http://localhost:${BACKEND_PORT}/api/health" >/dev/null 2>&1; then
  echo "✅ Backend  : http://localhost:${BACKEND_PORT}  (/api/health OK)"
else
  echo "⚠️  Backend  : NOT responding — check $BACKEND_LOG"
  tail -20 "$BACKEND_LOG" 2>/dev/null
fi
if curl -sf "http://localhost:${FRONTEND_PORT}/" >/dev/null 2>&1; then
  echo "✅ Frontend : http://localhost:${FRONTEND_PORT}"
else
  echo "⚠️  Frontend : NOT responding — check $FRONTEND_LOG"
  tail -20 "$FRONTEND_LOG" 2>/dev/null
fi

# --- local network IP ----------------------------------------------------------
EXT_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [ -n "$EXT_IP" ]; then
  echo ""
  echo "🌍 On this network, open:"
  echo "   http://${EXT_IP}:${FRONTEND_PORT}"
  echo "   (only reachable if the router forwards that port)"
fi
echo ""
echo "Done. To stop everything:  ./stop.sh   (use sudo to also close the ports)"