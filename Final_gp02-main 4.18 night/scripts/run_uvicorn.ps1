# Run FastAPI + Dash from the project root (the folder that contains `api/` and `research/`).
# Usage: .\scripts\run_uvicorn.ps1
# If you see "No module named 'api'", your current directory is wrong — use this script or:
#   cd "…\Final_gp02-main 4.18 night"
#   uvicorn api.main:app --host 0.0.0.0 --port 8000

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
Set-Location $root
$env:PYTHONPATH = $root
Write-Host "cwd: $root"
uvicorn api.main:app --host 0.0.0.0 --port 8000 @args
