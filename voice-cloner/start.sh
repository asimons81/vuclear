#!/bin/bash
#
# Vuclear Launcher - One-command startup for Mac/Linux/WSL
# Usage: ./start.sh [--check-only]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Vuclear..."

# ─── Dependency Check ─────────────────────────────────────────────────────────
check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 found"
        return 0
    else
        echo -e "${RED}✗${NC} $1 not found"
        return 1
    fi
}

echo ""
echo "Checking dependencies..."

# Check required commands
MISSING=0
check_command python3 || MISSING=1
check_command node || MISSING=1
check_command npm || MISSING=1
check_command ffmpeg || MISSING=1

if [ $MISSING -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}Missing dependencies detected.${NC}"
    echo ""
    echo "Install with:"
    echo ""
    echo "  # macOS (Homebrew)"
    echo "  brew install python node ffmpeg"
    echo ""
    echo "  # Ubuntu/Debian"
    echo "  sudo apt install python3 nodejs npm ffmpeg"
    echo ""
    echo "  # Windows (WSL)"
    echo "  sudo apt install python3 nodejs npm ffmpeg"
    echo ""
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_PYTHON="3.11"
if [ "$(printf '%s\n' "$REQUIRED_PYTHON" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON" ]; then
    echo -e "${RED}✗${NC} Python $PYTHON_VERSION found, but 3.11+ required"
    exit 1
else
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION"
fi

# Check Node version
NODE_VERSION=$(node -v | tr -d 'v')
REQUIRED_NODE="20"
if [ "$(printf '%s\n' "$REQUIRED_NODE" "$NODE_VERSION" | sort -V | head -n1)" != "$REQUIRED_NODE" ]; then
    echo -e "${RED}✗${NC} Node $NODE_VERSION found, but 20+ required"
    exit 1
else
    echo -e "${GREEN}✓${NC} Node $NODE_VERSION"
fi

# Check for optional voice engines
echo ""
echo "Checking voice engines..."

# Check if venv exists and use its pip
if [ -d ".venv" ]; then
    source .venv/bin/activate
    VENV_PIP="pip"
else
    VENV_PIP="pip3"
fi

if $VENV_PIP show chatterbox-tts &> /dev/null; then
    echo -e "${GREEN}✓${NC} Chatterbox TTS (MIT - Commercial OK)"
elif $VENV_PIP show metavoice &> /dev/null; then
    echo -e "${GREEN}✓${NC} MetaVoice (Apache 2.0 - Commercial OK)"
elif $VENV_PIP show f5-tts &> /dev/null; then
    echo -e "${YELLOW}!${NC} F5-TTS (CC-BY-NC - Non-commercial only)"
else
    echo -e "${YELLOW}!${NC} No voice engine installed"
    echo "  Install with: pip install chatterbox-tts"
fi

# ─── Check-only mode ─────────────────────────────────────────────────────────
if [ "$1" = "--check-only" ]; then
    echo ""
    echo -e "${GREEN}All checks passed!${NC}"
    exit 0
fi

# ─── Virtual Environment Setup ────────────────────────────────────────────────
echo ""
echo "Setting up Python environment..."

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install/update backend dependencies
if [ -f "backend/requirements.txt" ]; then
    pip install -r backend/requirements.txt --quiet 2>/dev/null || true
fi

# Check for at least one voice engine
if ! pip show chatterbox-tts &> /dev/null && ! pip show metavoice &> /dev/null && ! pip show f5-tts &> /dev/null; then
    echo ""
    echo -e "${YELLOW}Installing Chatterbox TTS (default engine)...${NC}"
    pip install chatterbox-tts
fi

# ─── Frontend Setup ────────────────────────────────────────────────────────────
echo ""
echo "Setting up frontend..."

if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# ─── Start Services ───────────────────────────────────────────────────────────
echo ""
echo "Starting services..."

# Start backend in background
echo "  → Backend: http://localhost:8000"
cd "$SCRIPT_DIR"
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend in background
echo "  → Frontend: http://localhost:3000"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Vuclear is ready!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Voice Setup:  http://localhost:3000"
echo "  Studio:       http://localhost:3000/studio"
echo "  API:          http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Handle cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
