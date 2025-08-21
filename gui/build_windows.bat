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
  --add-data "..\spotify\spotify_downloader.py;spotify" ^
  --add-data "..\spotify\.env;spotify" ^
  --add-data "..\instagram\instagram_downloader.py;instagram" ^
  --add-data "..\soundcloud\soundcloud_downloader.py;soundcloud" ^
  ..\gui\main.py

ECHO.
ECHO Build complete. Find the exe under dist\UniversalMediaDownloader.exe