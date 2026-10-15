@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" crear_administrador.py
if errorlevel 1 pause
