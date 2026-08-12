$ErrorActionPreference = 'Stop'

$MinerRoot = $PSScriptRoot
$Version = (Get-Content -LiteralPath (Join-Path $MinerRoot 'VERSION') -Raw).Trim()
$AppDirectory = Join-Path $MinerRoot 'dist\Dead Signal Miner'
$ReleaseDirectory = Join-Path $MinerRoot 'release\artifacts'
$Archive = Join-Path $ReleaseDirectory "Dead-Signal-Miner-v$Version-Windows.zip"

if (-not (Test-Path (Join-Path $AppDirectory 'Dead Signal Miner.exe'))) {
    throw 'Build the Miner before packaging a release.'
}
if (-not (Test-Path (Join-Path $AppDirectory 'Dead Signal Miner Updater.exe'))) {
    throw 'The updater helper is missing from the Miner build.'
}

New-Item -ItemType Directory -Path $ReleaseDirectory -Force | Out-Null
if (Test-Path $Archive) { Remove-Item -LiteralPath $Archive -Force }
Compress-Archive -LiteralPath $AppDirectory -DestinationPath $Archive -CompressionLevel Optimal
$Hash = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
$Size = (Get-Item -LiteralPath $Archive).Length
$Checksum = "$Hash  $(Split-Path -Leaf $Archive)"
Set-Content -LiteralPath "$Archive.sha256" -Value $Checksum -Encoding ascii

Write-Host "Package: $Archive"
Write-Host "SHA-256: $Hash"
Write-Host "Size: $Size"
Write-Host 'Upload the package first, then publish those exact values in release/latest.json.'

