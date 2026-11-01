$ErrorActionPreference='Stop'
Set-Location (Join-Path (Split-Path $PSScriptRoot -Parent) 'backend')
& ./.venv/Scripts/python.exe initialize_database.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& ./.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8088
