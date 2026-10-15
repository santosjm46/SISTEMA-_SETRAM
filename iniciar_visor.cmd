@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero ejecuta instalar_visor.ps1.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" visor_auditoria.py
if errorlevel 1 pause
