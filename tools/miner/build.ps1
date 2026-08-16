$ErrorActionPreference = 'Stop'

$MinerRoot = $PSScriptRoot
$Source = Join-Path $MinerRoot 'src'
$Build = Join-Path $MinerRoot 'build'
$Dist = Join-Path $MinerRoot 'dist'
$EnvironmentPython = Join-Path $MinerRoot '.venv-build\Scripts\python.exe'
$Python = if (Test-Path $EnvironmentPython) { $EnvironmentPython } else { 'python' }

foreach ($KnownOutput in @($Build, $Dist)) {
    if (Test-Path $KnownOutput) {
        Remove-Item -LiteralPath $KnownOutput -Recurse -Force
    }
}

$UpdaterArguments = @(
    '--noconfirm', '--clean', '--onefile', '--windowed',
    '--name', 'Dead Signal Miner Updater',
    '--icon', (Join-Path $MinerRoot 'assets\dead-signal-miner.ico'),
    '--distpath', (Join-Path $Dist 'updater'),
    '--workpath', (Join-Path $Build 'updater'),
    '--specpath', $Build,
    (Join-Path $Source 'miner_updater.py')
)
& $Python -m PyInstaller @UpdaterArguments
if ($LASTEXITCODE -ne 0) { throw 'Updater build failed.' }

$HiddenImports = @(
    'lz4.block', 'zstandard', 'PIL.Image', 'texture2ddecoder',
    'duckdb', 'polars', 'pyarrow',
    'npk_extract', 'export_bindict', 'export_marshaled_bindict',
    'normalize_armor', 'normalize_weapons', 'normalize_extended',
    'link_published_images', 'combat_resolver', 'weapon_progression',
    'publish_web_data', 'publish_extended_web_data', 'publish_current_calibrations',
    'armor_tier_normalization', 'armor_tier_completion',
    'mod_frame_enrichment', 'project_mod_frame_evidence',
    'weapon_evidence_enrichment', 'project_weapon_evidence',
    'research_console', 'research_window',
    'dead_signal_research_suite', 'dead_signal_research_cache', 'dead_signal_source_finder', 'dead_signal_table_profiler',
    'dead_signal_multihop_resolver', 'dead_signal_weapon_description_consumer', 'dead_signal_weapon_prototype_projection',
    'dead_signal_description_dataflow', 'dead_signal_description_dataflow_fallback', 'dead_signal_bindict_schema_audit',
    'dead_signal_blueprint_module_audit', 'dead_signal_common_data_registry_audit',
    'dead_signal_description_trace_compiler', 'dead_signal_description_flow_tab',
    'dead_signal_intelligence_window', 'dead_signal_intelligence_advanced', 'dead_signal_intelligence_hub',
    'dead_signal_discovery', 'dead_signal_discovery_tab',
    'dead_signal_verification', 'dead_signal_verification_tab',
    'dead_signal_analytics', 'dead_signal_evidence_graph', 'dead_signal_workflow_lab',
    'dead_signal_pipeline_inspector', 'dead_signal_publication_gate', 'neox_data_explorer',
    'reference_images', 'update_manager'
)
$MainArguments = @(
    '--noconfirm', '--clean', '--onedir', '--windowed',
    '--name', 'Dead Signal Miner',
    '--icon', (Join-Path $MinerRoot 'assets\dead-signal-miner.ico'),
    '--distpath', $Dist,
    '--workpath', (Join-Path $Build 'miner'),
    '--specpath', $Build,
    '--paths', $Source,
    '--paths', (Join-Path $Source 'extractor'),
    '--paths', (Join-Path $Source 'neoxtractor'),
    '--collect-all', 'PIL',
    '--collect-all', 'duckdb',
    '--collect-all', 'polars',
    '--collect-all', 'pyarrow',
    '--add-data', "$(Join-Path $Source 'extractor');extractor",
    '--add-data', "$(Join-Path $Source 'neoxtractor');neoxtractor",
    '--add-data', "$(Join-Path $MinerRoot 'assets\dead-signal-miner.ico');.",
    '--add-data', "$(Join-Path $MinerRoot 'README.md');.",
    '--add-data', "$(Join-Path $MinerRoot 'VERSION');."
)
foreach ($Module in $HiddenImports) {
    $MainArguments += @('--hidden-import', $Module)
}
$MainArguments += (Join-Path $Source 'miner_entry.py')

& $Python -m PyInstaller @MainArguments
if ($LASTEXITCODE -ne 0) { throw 'Miner build failed.' }

$AppDirectory = Join-Path $Dist 'Dead Signal Miner'
Copy-Item -LiteralPath (Join-Path $Dist 'updater\Dead Signal Miner Updater.exe') -Destination $AppDirectory -Force

Write-Host "Built: $(Join-Path $AppDirectory 'Dead Signal Miner.exe')"
