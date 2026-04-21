@echo off
REM Project root = parent of this scripts folder (must contain api\main.py)
set "ROOT=%~dp0.."
cd /d "%ROOT%"
set "PYTHONPATH=%CD%"
echo cwd: %CD%
uvicorn api.main:app --host 0.0.0.0 --port 8000 %*
