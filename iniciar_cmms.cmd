@echo off
cd /d "%~dp0"
if not exist ".env" (
  echo Configura PostgreSQL ejecutando instalar_cmms.ps1.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" servidor_local.py
if errorlevel 1 pause
