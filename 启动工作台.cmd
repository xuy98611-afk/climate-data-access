@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>&1
  if errorlevel 1 (
    python -m venv .venv
  ) else (
    py -3 -m venv .venv
  )
  if errorlevel 1 goto failed
)
if not exist ".venv\climate-workbench-0.2.ready" (
  ".venv\Scripts\python.exe" -m pip install -e ".[gee]"
  if errorlevel 1 goto failed
  type nul > ".venv\climate-workbench-0.2.ready"
)
".venv\Scripts\python.exe" -m climate_access serve --open
if errorlevel 1 goto failed
exit /b 0
:failed
echo Workbench could not start. Check Python 3.11+, installation output, and port 8765.
pause
exit /b 1
