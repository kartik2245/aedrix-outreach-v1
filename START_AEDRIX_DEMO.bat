@echo off
setlocal enabledelayedexpansion
title Aedrix AI Cold Outreach System - DEMO MODE
cd /d "%~dp0"

echo ===================================================================
echo  AEDRIX AI COLD OUTREACH SYSTEM - ONE-CLICK DEMO LAUNCHER
echo ===================================================================
echo.

REM 1. Verify Python Virtual Environment
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found (%~dp0.venv\Scripts\python.exe).
    echo Please create the virtual environment first:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM 2. Set Safe Demo Environment Variables
set "APP_MODE=DEMO"
set "DRY_RUN=true"
set "SEND_EMAILS=false"
set "SMARTLEAD_LIVE=false"
set "DEEPLINE_LIVE=false"

REM 3. Diagnostics & Safe Environment Setup
echo [1/2] Verifying Supabase PostgreSQL connection and safe demo mode...
call "%~dp0.venv\Scripts\python.exe" "%~dp0scripts\health_check.py" > nul 2>&1

REM 4. Check Frontend Build
echo [2/2] Checking operator dashboard assets...
if not exist "%~dp0frontend\dist\index.html" (
    echo Building frontend production bundle...
    cd /d "%~dp0frontend"
    call npm run build
    cd /d "%~dp0"
)

echo.
echo Starting Aedrix Operator API Server on http://localhost:8000 ...
echo.
echo ===================================================================
echo  STATUS: DEMO MODE ACTIVE
echo  SAFETY: Zero real emails dispatched, zero API credits consumed
echo  URL:    http://localhost:8000
echo ===================================================================
echo.
echo Launching your browser at http://localhost:8000 ...
echo Press Ctrl+C in this window to stop Aedrix.
echo.

REM 5. Open Browser in background after short delay
start "" cmd /c "ping 127.0.0.1 -n 3 > nul && start http://localhost:8000"

REM 6. Start Uvicorn Server with reload
call "%~dp0.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8000 --reload
