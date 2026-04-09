#!/usr/bin/env bash
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# ── colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════╗${NC}"
echo -e "${BLUE}║                VSSL              ║${NC}"
echo -e "${BLUE}║              110110001           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════╝${NC}"
echo ""

# ── backend ───────────────────────────────────────────────────────────────────
echo -e "${YELLOW}→ invoking backend on :5000${NC}"
cd "$SCRIPT_DIR"
uv run uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 5000 \
  --reload \
  --reload-dir backend \
  --log-level warning &
BACKEND_PID=$!
trap "kill $BACKEND_PID 2>/dev/null" EXIT INT TERM

echo -e "${GREEN}✓ backend pid $BACKEND_PID${NC}"

# ── wait for threshold ────────────────────────────────────────────────────────
echo -e "${YELLOW}→ waiting for backend...${NC}"
until curl -sf http://localhost:5000/api/health > /dev/null 2>&1; do
  sleep 0.5
done
echo -e "${GREEN}✓ backend ready${NC}"

# ── vessel ────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}→ opening vessel...${NC}"
cd "$SCRIPT_DIR/frontend"
cargo tauri dev
