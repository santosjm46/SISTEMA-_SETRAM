@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" configurar_cmms.py
if errorlevel 1 pause
