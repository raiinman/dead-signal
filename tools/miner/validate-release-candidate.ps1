param(
    [string]$Output = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Dead Signal Miner'),
    [int]$SamplePerDomain = 3,
    [int]$PerformanceSample = 20
)

$ErrorActionPreference = 'Stop'
$MinerRoot = $PSScriptRoot
$EnvironmentPython = Join-Path $MinerRoot '.venv-build\Scripts\python.exe'
$Python = if (Test-Path $EnvironmentPython) { $EnvironmentPython } else { 'python' }
$Source = Join-Path $MinerRoot 'src'
$Extractor = Join-Path $Source 'extractor'
$NeoX = Join-Path $Source 'neoxtractor'

$env:PYTHONPATH = "$Source;$Extractor;$NeoX"
Write-Host "Dead Signal real-snapshot release validation"
Write-Host "Output: $Output"

& $Python (Join-Path $Source 'dead_signal_release_candidate.py') `
    --output $Output `
    --sample-per-domain $SamplePerDomain `
    --performance-sample $PerformanceSample

if ($LASTEXITCODE -ne 0) {
    throw "Release-candidate validation failed. See $Output\reports\release-candidate-validation.json"
}

Write-Host "REAL SNAPSHOT GATE: GREEN"
Write-Host "Report: $Output\reports\release-candidate-validation.json"
