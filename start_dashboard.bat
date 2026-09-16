@echo off
setlocal enabledelayedexpansion
title Micropark MIS Dashboard
cd /d "%~dp0"

echo ==============================================================
echo   MICROPARK LOGISTICS - PHARMA OPERATIONS MIS
echo ==============================================================
echo.

REM ---------------------------------------------------------------- find Python
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY (
  python --version >nul 2>nul && set "PY=python"
)
if not defined PY goto :nopython

for /f "tokens=*" %%v in ('%PY% --version 2^>^&1') do set "PYVER=%%v"
echo Using !PYVER!
echo.

set "VPY=%~dp0venv\Scripts\python.exe"

REM ---------------------------------------------------------------- build the environment
if exist "venv" if not exist "%VPY%" (
  echo The setup folder is incomplete. Removing it and starting again.
  rmdir /s /q venv
)

if not exist "%VPY%" (
  echo First time setup. This needs an internet connection and takes 2-3 minutes.
  echo.
  %PY% -m venv venv
  if errorlevel 1 goto :venvfail
)

if not exist "%VPY%" goto :venvfail

REM ---------------------------------------------------------------- install packages
"%VPY%" -c "import fastapi, uvicorn, pandas, openpyxl" >nul 2>nul
if errorlevel 1 (
  echo Installing the required packages. Please wait, do not close this window.
  echo.
  "%VPY%" -m pip install --upgrade pip
  "%VPY%" -m pip install -r requirements.txt
  echo.
)

"%VPY%" -c "import fastapi, uvicorn, pandas, openpyxl" >nul 2>nul
if errorlevel 1 goto :pipfail

REM ---------------------------------------------------------------- start
echo Starting the dashboard...
echo.
"%VPY%" run_demo.py
goto :end

REM ---------------------------------------------------------------- problems
:nopython
echo.
echo   PYTHON IS NOT INSTALLED ON THIS COMPUTER
echo.
echo   Install Python 3.11 or later from https://www.python.org/downloads/
echo   On the first installer screen, tick "Add python.exe to PATH".
echo   Then run this file again.
echo.
echo   To show the demo right now without installing anything, open
echo   preview\dashboard_preview.html by double-clicking it.
echo.
goto :end

:venvfail
echo.
echo   COULD NOT CREATE THE SETUP FOLDER
echo.
echo   Your Python installation may be missing the venv module, or this
echo   folder may be read-only. Try moving the project to your Desktop
echo   and running it again.
echo.
echo   To show the demo right now, open preview\dashboard_preview.html.
echo.
goto :end

:pipfail
echo.
echo   THE PACKAGES DID NOT INSTALL
echo.
echo   Look at the messages above for the reason. The usual causes are
echo   no internet connection, or an office firewall or proxy blocking pip.
echo.
echo   If you are behind a company proxy, try this in a command window:
echo     "%VPY%" -m pip install -r requirements.txt --proxy http://user:pass@proxyserver:port
echo.
echo   To show the demo right now, open preview\dashboard_preview.html.
echo.
goto :end

:end
echo.
echo The dashboard has stopped. You can close this window.
pause
