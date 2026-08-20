@echo off
setlocal enabledelayedexpansion
title Aedrix AI Cold Outreach System - PRODUCTION MODE
cd /d "%~dp0\.."

set "APP_MODE=PRODUCTION"
set "DRY_RUN=true"
set "SEND_EMAILS=false"
set "SMARTLEAD_LIVE=false"
set "DEEPLINE_LIVE=false"

call "%~dp0..\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8000 --reload
