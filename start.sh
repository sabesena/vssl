#!/usr/bin/env bash
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
echo ""

# start backend on port 5000
echo -e "${YELLOW}→ invoking backend on :5000${NC}"
uv run uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 5000 \
  --reload \
  --reload-dir backend \
  --log-level warning &
BACKEND_PID=$!

echo -e "${GREEN}✓ backend pid $BACKEND_PID${NC}"
echo -e "${YELLOW}→ opening vessel...${NC}"
sleep 2

# launch tauri dev window
cd "$VSSL_DIR/frontend"
cargo tauri dev

# cleanup on exit
trap "kill $BACKEND_PID 2>/dev/null" EXIT INT TERM
