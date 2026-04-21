@echo off
cd /d "%~dp0Final_gp02-main 4.18 night"
if not exist "api\main.py" (
  echo ERROR: Run this from the folder that CONTAINS "Final_gp02-main 4.18 night", or cd into that subfolder and use scripts\run_uvicorn.bat
  pause
  exit /b 1
)
set "PYTHONPATH=%CD%"
echo cwd: %CD%
uvicorn api.main:app --host 0.0.0.0 --port 8000 %*
