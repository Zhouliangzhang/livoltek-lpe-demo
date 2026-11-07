$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& .venv/Scripts/python.exe baselines/validate_demo.py
if ($LASTEXITCODE -ne 0) { throw 'Original baseline validation failed.' }
& .venv/Scripts/python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
npm.cmd --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
npm.cmd --prefix frontend run test:e2e
if ($LASTEXITCODE -ne 0) { throw 'Browser workflow failed.' }
