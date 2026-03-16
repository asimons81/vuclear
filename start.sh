#!/usr/bin/env bash
#
# Vuclear Launcher — one-command startup for Linux / WSL / macOS
# Usage: ./start.sh [--check-only]
#
# Does NOT use `set -e` globally because we background long-running processes
# and want to handle their failures explicitly rather than silently.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ─── State ────────────────────────────────────────────────────────────────────
BACKEND_PID=""
FRONTEND_PID=""
BACKEND_LOG="$(mktemp /tmp/vuclear-backend.XXXXXX.log)"

# ─── Helpers ──────────────────────────────────────────────────────────────────
die() {
    echo -e "${RED}ERROR:${NC} $*" >&2
    exit 1
}

ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
warn() { echo -e "  ${YELLOW}!${NC} $*"; }
fail() { echo -e "  ${RED}✗${NC} $*"; }

check_command() {
    if command -v "$1" &>/dev/null; then
        ok "$1 found"
        return 0
    else
        fail "$1 not found"
        return 1
    fi
}

# ─── Cleanup on Ctrl-C / SIGTERM ─────────────────────────────────────────────
# Registered immediately so it is in place for the entire script lifetime.
cleanup() {
    echo ""
    echo "Stopping services..."
    [ -n "$BACKEND_PID"  ] && kill "$BACKEND_PID"  2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
    # Keep the backend log around only if backend failed; otherwise remove it.
    [ -f "$BACKEND_LOG"  ] && rm -f "$BACKEND_LOG"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ─── Python Selection ─────────────────────────────────────────────────────────
echo ""
echo "🚀 Starting Vuclear..."
echo ""
echo "Checking dependencies..."

PYTHON_CMD=""
for candidate in python3 python3.13 python3.12 python3.11; do
    if command -v "$candidate" &>/dev/null; then
        _ver=$("$candidate" -c \
            'import sys; print(".".join(map(str, sys.version_info[:2])))' \
            2>/dev/null) || continue
        _major=$(echo "$_ver" | cut -d. -f1)
        _minor=$(echo "$_ver" | cut -d. -f2)
        if [ "$_major" -eq 3 ] && [ "$_minor" -ge 11 ] && [ "$_minor" -le 13 ]; then
            PYTHON_CMD="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    die "No compatible Python (3.11–3.13) found. Install from https://python.org"
fi

PYTHON_VERSION=$("$PYTHON_CMD" -c \
    'import sys; print(".".join(map(str, sys.version_info[:2])))')
ok "Python $PYTHON_VERSION"

# ─── Other Dependencies ───────────────────────────────────────────────────────
MISSING=0
check_command node   || MISSING=1
check_command npm    || MISSING=1
check_command ffmpeg || MISSING=1

if [ "$MISSING" -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}Install missing tools:${NC}"
    echo "  Ubuntu/Debian/WSL:  sudo apt install nodejs npm ffmpeg"
    echo "  macOS (Homebrew):   brew install node ffmpeg"
    exit 1
fi

# Node version ≥ 20 check
NODE_VERSION=$(node -v | tr -d 'v')
REQUIRED_NODE="20"
if [ "$(printf '%s\n' "$REQUIRED_NODE" "$NODE_VERSION" | sort -V | head -n1)" \
     != "$REQUIRED_NODE" ]; then
    die "Node $NODE_VERSION found, but 20+ required."
fi
ok "Node $NODE_VERSION"

# ─── Check-only mode ─────────────────────────────────────────────────────────
if [ "${1:-}" = "--check-only" ]; then
    echo ""
    echo -e "${GREEN}All checks passed.${NC}"
    exit 0
fi

# ─── Virtual Environment ──────────────────────────────────────────────────────
echo ""
echo "Setting up Python environment..."

if [ -d ".venv" ]; then
    # Verify the existing venv uses a compatible Python (3.11–3.13).
    # A mismatch (e.g. venv created with 3.14 while pyenv selects 3.11)
    # causes pip to install packages into the wrong interpreter's site-packages,
    # which breaks imports at runtime.
    _venv_python=".venv/bin/python"
    if [ -x "$_venv_python" ]; then
        _venv_ver=$("$_venv_python" -c \
            'import sys; print(".".join(map(str, sys.version_info[:2])))' \
            2>/dev/null) || _venv_ver=""
        _venv_minor=$(echo "$_venv_ver" | cut -d. -f2)
        _venv_major=$(echo "$_venv_ver" | cut -d. -f1)
        if [ -z "$_venv_ver" ] \
           || [ "$_venv_major" -ne 3 ] \
           || [ "$_venv_minor" -lt 11 ] \
           || [ "$_venv_minor" -gt 13 ]; then
            warn "Existing .venv uses Python ${_venv_ver:-unknown} (need 3.11–3.13). Recreating..."
            rm -rf .venv
        fi
    fi
fi

if [ ! -d ".venv" ]; then
    echo "  Creating virtual environment..."
    "$PYTHON_CMD" -m venv .venv || die "Failed to create .venv"
fi

# shellcheck source=/dev/null
source .venv/bin/activate

# Install backend dependencies — errors are visible, NOT swallowed
if [ -f "backend/requirements.txt" ]; then
    echo "  Installing backend dependencies (this may take a moment)..."
    pip install -r backend/requirements.txt -q \
        || die "pip install failed — see errors above"
fi

# Ensure at least one voice engine is present
if ! pip show chatterbox-tts &>/dev/null \
   && ! pip show metavoice      &>/dev/null \
   && ! pip show f5-tts         &>/dev/null; then
    echo ""
    warn "No voice engine found. Installing Chatterbox TTS (MIT)..."
    pip install --upgrade pip setuptools wheel -q
    pip install chatterbox-tts \
        || die "Voice engine install failed — see errors above"
fi

# ─── Frontend Dependencies ────────────────────────────────────────────────────
echo ""
echo "Setting up frontend..."

if [ ! -d "frontend/node_modules" ]; then
    echo "  Installing frontend dependencies..."
    ( cd "$SCRIPT_DIR/frontend" && npm install ) \
        || die "npm install failed"
fi

# ─── Start Backend ────────────────────────────────────────────────────────────
echo ""
echo "Starting services..."
echo "  → Backend:  http://localhost:8000"

# Re-source venv in case a subshell changed it
source .venv/bin/activate

# Stdout and stderr both go to the log file so we can cat them on failure.
# The -n flag enables colorised logs when writing to a non-tty, but we drop
# that for simplicity — the file will contain plain text.
uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# ─── Backend Health-Check ─────────────────────────────────────────────────────
# Poll /api/v1/health up to 20 times (1s apart = 20s max).
#
# Health contract: the endpoint returns HTTP 200 as soon as the API process
# is accepting connections — regardless of whether the voice model has finished
# loading. Model loading happens in the background and may take 60–120s.
# engine_loading=true in the JSON body is normal immediately after startup.
#
# If the process dies during polling, bail immediately with the log.

echo -n "  Waiting for backend API to come up"
HEALTH_OK=0
for _i in $(seq 1 20); do
    sleep 1

    # Is the process still alive?
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo ""
        echo -e "${RED}Backend process exited during startup.${NC}"
        echo "─── Backend log ────────────────────────────────────────────"
        cat "$BACKEND_LOG"
        echo "────────────────────────────────────────────────────────────"
        rm -f "$BACKEND_LOG"
        BACKEND_LOG=""
        die "Backend failed to start. Fix the errors above and retry."
    fi

    # Is it responding? (short timeout — endpoint is non-blocking now)
    if curl -sf --max-time 3 \
            http://localhost:8000/api/v1/health \
            -o /dev/null 2>/dev/null; then
        HEALTH_OK=1
        break
    fi

    echo -n "."
done
echo ""  # newline after the dots

if [ "$HEALTH_OK" -eq 0 ]; then
    echo -e "${RED}Backend API did not respond within 20 seconds.${NC}"
    echo "─── Backend log ────────────────────────────────────────────"
    cat "$BACKEND_LOG"
    echo "────────────────────────────────────────────────────────────"
    kill "$BACKEND_PID" 2>/dev/null || true
    rm -f "$BACKEND_LOG"
    BACKEND_LOG=""
    die "Backend startup timed out. Check the log above."
fi

ok "Backend API up (PID $BACKEND_PID)"
warn "Voice model is loading in the background — first synthesis may be slow"

# ─── Start Frontend ───────────────────────────────────────────────────────────
echo "  → Frontend: http://localhost:3000"
( cd "$SCRIPT_DIR/frontend" && npm run dev ) &
FRONTEND_PID=$!

# ─── Ready ────────────────────────────────────────────────────────────────────
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
echo "  Backend log:  $BACKEND_LOG"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for both processes — the trap handles Ctrl-C
wait $BACKEND_PID $FRONTEND_PID
