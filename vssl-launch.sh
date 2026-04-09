#!/usr/bin/env bash
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$SCRIPT_DIR"

# ── backend ───────────────────────────────────────────────────────────────────
source .venv/bin/activate 2>/dev/null || true
nohup uv run uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 5000 \
  --reload-dir backend \
  --log-level warning \
  > /tmp/vssl-backend.log 2>&1 &

# ── wait for threshold ────────────────────────────────────────────────────────
for i in $(seq 1 15); do
  curl -sf http://localhost:5000/api/health > /dev/null 2>&1 && break
  sleep 1
done

export GDK_SCALE=1
export GDK_DPI_SCALE=1
export QT_AUTO_SCREEN_SCALE_FACTOR=0
export WEBKIT_DISABLE_DMABUF_RENDERER=1

# ── vessel ────────────────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/frontend"
exec cargo tauri dev
