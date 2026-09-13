@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist "apps\api\.venv\Scripts\python.exe" (
  echo API Python environment is missing. See README.md.
  if /I not "%GAVIN_LAUNCHER_NO_PAUSE%"=="1" pause
  exit /b 1
)
"apps\api\.venv\Scripts\python.exe" -B "scripts\local_launcher.py" stop
set "LAUNCH_RESULT=%ERRORLEVEL%"
if /I not "%GAVIN_LAUNCHER_NO_PAUSE%"=="1" pause
exit /b %LAUNCH_RESULT%
