@echo off
REM Vuclear Launcher - One-command startup for Windows
REM Usage: start.bat

echo.
echo 🚀 Starting Vuclear...
echo.

REM ─── Python Interpreter Selection ─────────────────────────────────────────────
echo Finding compatible Python...

REM Try to find Python 3.11-3.13 (known compatible range)
REM Python 3.14+ has setuptools/pip compatibility issues
set PYTHON_CMD=

REM Check for specific versions
where python3.13 >nul 2>&1 && set PYTHON_CMD=python3.13
if defined PYTHON_CMD goto :python_found
where python3.12 >nul 2>&1 && set PYTHON_CMD=python3.12
if defined PYTHON_CMD goto :python_found
where python3.11 >nul 2>&1 && set PYTHON_CMD=python3.11
if defined PYTHON_CMD goto :python_found

REM Fall back to python
where python >nul 2>&1 && set PYTHON_CMD=python

:python_found
if not defined PYTHON_CMD (
    echo ✗ No Python interpreter found
    echo   Install Python 3.11-3.13 from https://python.org
    pause
    exit /b 1
)

REM Check Python version
for /f "delims=" %%v in ('%PYTHON_CMD% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PYTHON_VERSION=%%v
echo Using Python %PYTHON_VERSION%...

REM Enforce compatible range: 3.11 <= version <= 3.13
echo %PYTHON_VERSION% | findstr /R "^3\.[0-9][0-9]*$" >nul
if errorlevel 1 (
    echo ✗ Cannot determine Python version
    pause
    exit /b 1
)

for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)

set COMPATIBLE=0
if "%PYTHON_MAJOR%"=="3" (
    if %PYTHON_MINOR% GEQ 11 (
        if %PYTHON_MINOR% LEQ 13 (
            set COMPATIBLE=1
        )
    )
)

if %COMPATIBLE%==0 (
    echo ✗ Python %PYTHON_VERSION% found
    echo   Vuclear requires Python 3.11, 3.12, or 3.13
    echo   Python 3.14+ has compatibility issues
    echo.
    echo Install a compatible version:
    echo   https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✓ Python %PYTHON_VERSION% (compatible)

REM ─── Dependency Check ─────────────────────────────────────────────────────────
echo.
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
    %PYTHON_CMD% -m venv .venv
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
            echo Ensuring packaging tools are up-to-date...
            pip install --upgrade pip setuptools wheel >nul 2>&1
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
