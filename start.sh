#!/usr/bin/env bash
set -e

VSSL_DIR="/mnt/1TB/vssl"
cd "$VSSL_DIR"

# ── colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════╗${NC}"
echo -e "${BLUE}║                VSSL              ║${NC}"
echo -e "${BLUE}║              110110001           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════╝${NC}"

# ── parse args ───────────────────────────────────────────────────────────────
DEV=false
BUILD=false

for arg in "$@"; do
  case "$arg" in
    --dev)   DEV=true ;;
    --build) BUILD=true ;;
  esac
done

# ── install python deps ───────────────────────────────────────────────────────
echo -e "${YELLOW}→ Installing Python dependencies...${NC}"
uv sync --quiet 2>/dev/null || uv pip install fastapi "uvicorn[standard]" httpx psutil python-multipart 2>/dev/null || true

# ── frontend setup ────────────────────────────────────────────────────────────
if [ ! -d "$VSSL_DIR/frontend/node_modules" ]; then
  echo -e "${YELLOW}→ Installing frontend dependencies...${NC}"
  cd "$VSSL_DIR/frontend" && npm install --silent
  cd "$VSSL_DIR"
fi

# ── build or dev mode ─────────────────────────────────────────────────────────
if [ "$DEV" = true ]; then
  echo -e "${GREEN}→ Starting in DEV mode${NC}"
  echo -e "  Backend:  http://localhost:5000"
  echo -e "  Frontend: http://localhost:5173 (with hot reload)"
  echo ""

  # start backend
  uv run uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 5000 \
    --reload \
    --reload-dir backend \
    --log-level warning &
  BACKEND_PID=$!

  # start frontend dev server
  cd "$VSSL_DIR/frontend" && npm run dev &
  FRONTEND_PID=$!

  echo -e "${GREEN}✓ vssl running! Open http://localhost:5173${NC}"

  # cleanup on exit
  trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'vssl stopped.'" EXIT INT TERM
  wait

else
  # production: build frontend, serve everything from FastAPI
  if [ "$BUILD" = true ] || [ ! -d "$VSSL_DIR/frontend/dist" ]; then
    echo -e "${YELLOW}→ Building frontend...${NC}"
    cd "$VSSL_DIR/frontend" && npm run build
    cd "$VSSL_DIR"
    echo -e "${GREEN}✓ Frontend built${NC}"
  fi

  echo -e "${GREEN}→ Starting vssl at http://localhost:5000${NC}"
  echo ""
  uv run uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 5000 \
    --workers 1 \
    --log-level info
fi
