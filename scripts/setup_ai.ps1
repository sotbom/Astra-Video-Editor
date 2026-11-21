$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
if (-not (Test-Path '.venv-ai/Scripts/python.exe')) {
    & '.venv/Scripts/python.exe' -m venv .venv-ai
    if ($LASTEXITCODE -ne 0) { throw 'AI environment creation failed' }
}
& '.venv-ai/Scripts/python.exe' -m pip install --only-binary=:all: -r requirements-ai-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'AI dependency installation failed' }
& '.venv-ai/Scripts/python.exe' -m pip check
if ($LASTEXITCODE -ne 0) { throw 'AI dependency check failed' }
Write-Output 'AI environment ready. Download a model explicitly from the editor.'
