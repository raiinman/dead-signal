@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src;%~dp0src\extractor;%~dp0src\neoxtractor;%PYTHONPATH%"
pythonw.exe src\dead_signal_miner.py
if errorlevel 1 (
  python.exe src\dead_signal_miner.py
  pause
)
