$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment creation failed.' }
}
# Host pip can bootstrap the isolated environment even if ensurepip was unavailable.
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment refresh failed.' }
python -m pip --python .venv/Scripts/python.exe install -r backend/requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed. Check network access to PyPI.' }
Push-Location frontend
try {
    if (Test-Path package-lock.json) { npm.cmd ci --cache ../.npm-cache } else { npm.cmd install --cache ../.npm-cache }
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
} finally { Pop-Location }
& .venv/Scripts/python.exe baselines/validate_demo.py
if ($LASTEXITCODE -ne 0) { throw 'Baseline validation failed.' }
Write-Host 'Dependencies installed and original baselines validated.'
