@echo off
REM Vuclear Launcher - One-command startup for Windows
REM Usage: start.bat

echo.
echo 🚀 Starting Vuclear...
echo.

REM ─── Dependency Check ─────────────────────────────────────────────────────────
echo Checking dependencies...

REM Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Python not found
    goto :missing_deps
)
python --version >nul 2>&1 || (
    echo ✗ Python not working
    goto :missing_deps
)
echo ✓ Python found

REM Check Node
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Node.js not found
    goto :missing_deps
)
echo ✓ Node.js found

REM Check npm
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ npm not found
    goto :missing_deps
)
echo ✓ npm found

REM Check FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ FFmpeg not found
    goto :missing_deps
)
echo ✓ FFmpeg found

echo.
goto :setup_venv

:missing_deps
echo.
echo Missing dependencies detected.
echo.
echo Install with:
echo.
echo   # Using Chocolatey
echo   choco install python nodejs ffmpeg
echo.
echo   # Or download from:
echo   #   Python:   https://python.org
echo   #   Node.js:  https://nodejs.org
echo   #   FFmpeg:   https://ffmpeg.org
echo.
pause
exit /b 1

:setup_venv
REM ─── Virtual Environment Setup ────────────────────────────────────────────────
echo.
echo Setting up Python environment...

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate venv
call .venv\Scripts\activate.bat

REM Install/update backend dependencies
if exist "backend\requirements.txt" (
    pip install -r backend\requirements.txt --quiet 2>nul || echo Warning: Some packages may need manual install
)

REM Check for at least one voice engine
pip show chatterbox-tts >nul 2>&1
if %errorlevel% neq 0 (
    pip show metavoice >nul 2>&1
    if %errorlevel% neq 0 (
        pip show f5-tts >nul 2>&1
        if %errorlevel% neq 0 (
            echo.
            echo Installing Chatterbox TTS...
            pip install chatterbox-tts
        )
    )
)

REM ─── Frontend Setup ────────────────────────────────────────────────────────────
echo.
echo Setting up frontend...

if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

REM ─── Start Services ───────────────────────────────────────────────────────────
echo.
echo Starting services...

REM Start backend
echo   → Backend: http://localhost:8000
start "Vuclear Backend" cmd /k "call .venv\Scripts\activate.bat && uvicorn backend.main:app --host 0.0.0.0 --port 8000"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend
echo   → Frontend: http://localhost:3000
start "Vuclear Frontend" cmd /k "cd frontend && npm run dev"

REM ─── Done ─────────────────────────────────────────────────────────────────────
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   Vuclear is ready!
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo   Voice Setup:  http://localhost:3000
echo   Studio:       http://localhost:3000/studio
echo   API:          http://localhost:8000
echo   API Docs:     http://localhost:8000/docs
echo.
echo Close these windows to stop the servers.
echo.

pause
