@echo off
REM ============================================================================
REM  Reassembles the multi-part translator-offline-3.3B.zip and verifies it.
REM  Put ALL of these in one folder, then double-click this file:
REM    translator-offline-3.3B.zip.part00
REM    translator-offline-3.3B.zip.part01
REM    translator-offline-3.3B.zip.part02
REM    reassemble-3.3B.bat  (this file)
REM ============================================================================
setlocal
cd /d "%~dp0"

if not exist "translator-offline-3.3B.zip.part00" (
  echo Cannot find the .part files. Put this .bat in the same folder as the parts.
  pause & exit /b 1
)

echo Reassembling translator-offline-3.3B.zip ...
copy /b "translator-offline-3.3B.zip.part*" "translator-offline-3.3B.zip" >nul
if not exist "translator-offline-3.3B.zip" ( echo FAILED. & pause & exit /b 1 )

echo Verifying checksum ...
set "EXPECTED=6eb7c9761c2021b025a32aa2ce4a9bf1912ba31118643892c4817a2ee67c7c70"
set "ACTUAL="
for /f "usebackq skip=1 delims=" %%H in (`certutil -hashfile "translator-offline-3.3B.zip" SHA256`) do if not defined ACTUAL set "ACTUAL=%%H"
set "ACTUAL=%ACTUAL: =%"

if /i "%ACTUAL%"=="%EXPECTED%" (
  echo.
  echo OK - checksum matches. Unzip translator-offline-3.3B.zip, then run run-gui.bat inside it.
  echo You can delete the .part files now.
) else (
  echo.
  echo WARNING: checksum does not match - a part may be corrupt or incomplete.
  echo   expected: %EXPECTED%
  echo   got:      %ACTUAL%
  echo Re-download the parts and run this again.
)
echo.
pause
