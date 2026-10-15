$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno.' }
}
& .\.venv\Scripts\python.exe -m pip install -r requirements_cmms.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }
& .\.venv\Scripts\python.exe descargar_bootstrap.py
if ($LASTEXITCODE -ne 0) { throw 'No se pudo descargar Bootstrap.' }
if (-not (Test-Path -LiteralPath '.env')) { & .\.venv\Scripts\python.exe configurar_cmms.py }
if (-not (Test-Path -LiteralPath '.env')) { throw 'La conexión a CMMS no fue guardada.' }
& .\.venv\Scripts\python.exe manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron aplicar las migraciones.' }
& .\.venv\Scripts\python.exe manage.py inicializar_setram
if ($LASTEXITCODE -ne 0) { throw 'No se pudo inicializar SETRAM.' }
& .\.venv\Scripts\python.exe crear_administrador.py
Write-Host 'Listo. Ejecuta iniciar_cmms.cmd y entra en http://127.0.0.1:8000'
