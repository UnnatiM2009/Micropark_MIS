@echo off
setlocal
title Add logo - Micropark MIS Dashboard
cd /d "%~dp0"

if "%~1"=="" (
  echo.
  echo   HOW TO USE THIS
  echo.
  echo   Drag your logo image file and drop it onto this add_logo.bat file.
  echo   That is all. The dashboard will start using it.
  echo.
  echo   Accepted: .png  .svg  .jpg  .jpeg  .webp  .gif
  echo   A PNG with a transparent background looks best.
  echo.
  pause
  exit /b 0
)

set "PY="
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"
if not defined PY (
  py -3 --version >nul 2>nul && set "PY=py -3"
)
if not defined PY (
  python --version >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo Python was not found. Install it, or copy your logo by hand into:
  echo   app\static\img\logo.png
  pause
  exit /b 1
)

%PY% scripts\add_logo.py "%~1"
echo.
pause
