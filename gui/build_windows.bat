@echo off
REM Build single-file Windows .exe using PyInstaller
REM Prerequisites (in venv recommended):
REM   pip install -r ..\gui\requirements.txt
REM   pip install pyinstaller

set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

IF NOT EXIST dist mkdir dist

pyinstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "UniversalMediaDownloader" ^
  --add-data "..\youtube\cookies.txt;youtube" ^
  ..\gui\main.py

ECHO.
ECHO Build complete. Find the exe under dist\UniversalMediaDownloader.exe