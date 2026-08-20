@echo off
setlocal enabledelayedexpansion
title Stop Aedrix Background Services
echo ===================================================================
echo  AEDRIX PROCESS TERMINATOR
echo ===================================================================
echo.
echo Stopping any running Aedrix FastAPI or Vite dev processes...

powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

echo.
echo All Aedrix processes stopped cleanly.
echo ===================================================================
ping 127.0.0.1 -n 2 > nul
