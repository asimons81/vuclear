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

# ─── Python Interpreter Selection ────────────────────────────────────────────────
echo ""
echo "Finding compatible Python..."

# First check if default python3 is already compatible
# This is preferred because it typically has venv support available
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' 2>/dev/null) || true
    if [ -n "$PYTHON_VERSION" ]; then
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ] && [ "$PYTHON_MINOR" -le 13 ]; then
            PYTHON_CMD="python3"
        fi
    fi
fi

# If python3 isn't compatible, try specific versions
if [ -z "$PYTHON_CMD" ]; then
    for ver in 3.11 3.12 3.13; do
        if command -v python$ver &> /dev/null; then
            PYTHON_CMD="python$ver"
            break
        fi
    done
fi

# Final check - must have SOME Python
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}✗${NC} No Python interpreter found"
    echo "Install Python 3.11-3.13 from https://python.org"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

# Enforce compatible range: 3.11 <= version <= 3.13
if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ] && [ "$PYTHON_MINOR" -le 13 ]; then
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION (compatible)"
else
    echo -e "${RED}✗${NC} Python $PYTHON_VERSION found"
    echo "  Vuclear requires Python 3.11, 3.12, or 3.13"
    echo "  Python 3.14+ has compatibility issues with voice engines"
    echo ""
    echo "Install a compatible version:"
    echo "  https://www.python.org/downloads/"
    exit 1
fi

# Check required commands
MISSING=0
check_command $PYTHON_CMD || MISSING=1
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
else
    # In check-only mode without venv, skip voice engine check
    if [ "$1" = "--check-only" ]; then
        echo ""
        echo -e "${YELLOW}!${NC} No voice engine check (no venv yet)"
        echo "  Voice engine will be installed when you run without --check-only"
    else
        echo -e "${YELLOW}!${NC} No voice engine installed"
        echo "  Install with: pip install chatterbox-tts"
    fi
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
    echo "Creating virtual environment with $PYTHON_CMD..."
    $PYTHON_CMD -m venv .venv
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
    echo -e "${YELLOW}Ensuring packaging tools are up-to-date...${NC}"
    pip install --upgrade pip setuptools wheel --quiet
    
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
