@echo off
setlocal enabledelayedexpansion
title Aedrix AI Cold Outreach System - PRODUCTION MODE
cd /d "%~dp0"

echo ===================================================================
echo  AEDRIX AI COLD OUTREACH SYSTEM - PRODUCTION LAUNCHER
echo ===================================================================
echo.

REM 1. Verify Python Virtual Environment
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found (%~dp0.venv\Scripts\python.exe).
    pause
    exit /b 1
)

REM 2. Set Production Environment Variables
set "APP_MODE=PRODUCTION"
set "DRY_RUN=false"
set "DEEPLINE_LIVE=true"
set "DEEPLINE_RUN_CONFIRMATION=true"
set "SMARTLEAD_LIVE=false"
set "SEND_EMAILS=false"
set "PRODUCTION_SEND_CONFIRMATION=false"

echo [1/2] Verifying Supabase PostgreSQL connection...
call "%~dp0.venv\Scripts\python.exe" "%~dp0scripts\health_check.py" > nul 2>&1

echo [2/2] Checking operator dashboard assets...
if not exist "%~dp0frontend\dist\index.html" (
    echo Building frontend production bundle...
    cd /d "%~dp0frontend"
    call npm run build
    cd /d "%~dp0"
)

echo.
echo Starting Aedrix Operator API Server on http://0.0.0.0:8000 ...
echo.
echo ===================================================================
echo  STATUS: PRODUCTION MODE (LIVE PROCESSING — EMAIL DELIVERY OFF)
echo  SAFETY: Strict Human Approval Gate active before any staging
echo  URL:    http://localhost:8000
echo ===================================================================
echo.
echo Launching your browser at http://localhost:8000 ...
echo Press Ctrl+C in this window to stop Aedrix.
echo.

start "" cmd /c "ping 127.0.0.1 -n 3 > nul && start http://localhost:8000"

call "%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
