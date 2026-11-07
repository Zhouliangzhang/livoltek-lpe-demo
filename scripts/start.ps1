$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path '.venv/Scripts/python.exe')) { throw 'Run scripts/setup.ps1 first.' }
npm.cmd --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
Write-Host 'Open http://127.0.0.1:8000 — press Ctrl+C to stop.'
& .venv/Scripts/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
