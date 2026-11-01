Set-Location (Join-Path (Split-Path $PSScriptRoot -Parent) 'backend')
New-Item -ItemType Directory -Path test-results -Force | Out-Null
& ./.venv/Scripts/python.exe -m pytest tests -q --tb=short --junitxml=test-results/recheck90.xml
exit $LASTEXITCODE
