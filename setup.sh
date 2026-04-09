#!/usr/bin/env bash
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# ── colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════╗${NC}"
echo -e "${BLUE}║                VSSL              ║${NC}"
echo -e "${BLUE}║              110110001           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════╝${NC}"
echo ""

# ── dependency checks ─────────────────────────────────────────────────────────
MISSING=0

check_dep() {
  if ! command -v "$1" &> /dev/null; then
    echo -e "${RED}✗ $1 not found — $2${NC}"
    MISSING=1
  else
    echo -e "${GREEN}✓ $1${NC}"
  fi
}

check_dep ollama  "https://ollama.ai"
check_dep python3 "python 3.11+ — https://python.org"
check_dep uv      "curl -LsSf https://astral.sh/uv/install.sh | sh"
check_dep node    "node 18+ — https://nodejs.org"

if [ $MISSING -ne 0 ]; then
  echo ""
  echo -e "${RED}✗ missing dependencies — install above and rerun${NC}"
  exit 1
fi

echo ""

# ── python deps ───────────────────────────────────────────────────────────────
echo -e "${YELLOW}→ installing python dependencies${NC}"
cd "$SCRIPT_DIR"
uv sync || { echo -e "${RED}✗ uv sync failed${NC}"; exit 1; }
echo -e "${GREEN}✓ python deps ready${NC}"

# ── frontend deps ─────────────────────────────────────────────────────────────
echo -e "${YELLOW}→ installing frontend dependencies${NC}"
cd "$SCRIPT_DIR/frontend"
npm install || { echo -e "${RED}✗ npm install failed${NC}"; exit 1; }
echo -e "${GREEN}✓ frontend deps ready${NC}"

echo ""
echo -e "${GREEN}✦ vessel prepared${NC}"
echo -e "  start:  ${BLUE}./start.sh${NC}"
echo -e "  open:   ${BLUE}http://localhost:5000${NC}"
