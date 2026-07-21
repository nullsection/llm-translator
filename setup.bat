@echo off
REM One-time setup: installs uv + Python deps, then downloads the translation
REM model you choose plus the English/Chinese/Japanese voices.
REM Usage:  setup.bat            (default 1.3B)
REM         setup.bat 600M       setup.bat 3.3B
setlocal
cd /d "%~dp0"
set "MODEL=%~1"
if "%MODEL%"=="" set "MODEL=1.3B"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
set "PYTHONUTF8=1"

echo === Offline Voice Translator setup (translation model: %MODEL%) ===

where uv >nul 2>&1
if errorlevel 1 (
  echo Installing uv ...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
)
where uv >nul 2>&1
if errorlevel 1 (
  echo Could not find uv. Install it from https://docs.astral.sh/uv/ then re-run setup.bat
  pause & exit /b 1
)

echo Installing Python dependencies ...
uv sync
if errorlevel 1 goto fail

echo Downloading model + voices ...
set "TRANSLATOR_NLLB_MODEL=%MODEL%"
uv run translator setup-models --model %MODEL%
if errorlevel 1 goto fail

echo.
echo Setup complete. Launch with:  run-gui.bat
echo.
exit /b 0

:fail
echo.
echo Setup FAILED - see messages above.
pause
exit /b 1
