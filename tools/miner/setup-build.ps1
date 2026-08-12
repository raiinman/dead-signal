$ErrorActionPreference = 'Stop'

$MinerRoot = $PSScriptRoot
$Environment = Join-Path $MinerRoot '.venv-build'

if (-not (Test-Path (Join-Path $Environment 'Scripts\python.exe'))) {
    python -m venv $Environment
}

$Python = Join-Path $Environment 'Scripts\python.exe'
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $MinerRoot 'requirements-build.txt')

Write-Host "Build environment ready: $Environment"

