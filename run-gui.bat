@echo off
REM Launch the desktop translator (run setup.bat first).
setlocal
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
set "TRANSLATOR_HOME=%~dp0models"
set "PYTHONUTF8=1"

if not exist "%~dp0.venv" (
  echo Please run setup.bat first to install dependencies and a model.
  pause & exit /b 1
)

uv run translator gui
if errorlevel 1 pause
