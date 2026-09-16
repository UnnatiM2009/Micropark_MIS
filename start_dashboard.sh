#!/usr/bin/env bash
# Micropark MIS Dashboard - run this to start the demo (Mac or Linux).
set -u
cd "$(dirname "$0")" || exit 1

echo "=============================================================="
echo "  MICROPARK LOGISTICS - PHARMA OPERATIONS MIS"
echo "=============================================================="
echo

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "  PYTHON IS NOT INSTALLED"
  echo "  Install it from https://www.python.org/downloads/ and run this again."
  echo "  To show the demo right now, open preview/dashboard_preview.html."
  exit 1
fi

echo "Using $($PY --version 2>&1)"
echo

VPY="venv/bin/python"

if [ -d venv ] && [ ! -x "$VPY" ]; then
  echo "The setup folder is incomplete. Removing it and starting again."
  rm -rf venv
fi

if [ ! -x "$VPY" ]; then
  echo "First time setup. This needs an internet connection and takes 2-3 minutes."
  echo
  if ! $PY -m venv venv; then
    echo
    echo "  COULD NOT CREATE THE SETUP FOLDER"
    echo "  On Debian or Ubuntu you may need:  sudo apt install python3-venv"
    echo "  To show the demo right now, open preview/dashboard_preview.html."
    exit 1
  fi
fi

if ! "$VPY" -c "import fastapi, uvicorn, pandas, openpyxl" >/dev/null 2>&1; then
  echo "Installing the required packages. Please wait."
  echo
  "$VPY" -m pip install --upgrade pip
  "$VPY" -m pip install -r requirements.txt
  echo
fi

if ! "$VPY" -c "import fastapi, uvicorn, pandas, openpyxl" >/dev/null 2>&1; then
  echo
  echo "  THE PACKAGES DID NOT INSTALL"
  echo "  Check the messages above. The usual cause is no internet, or a proxy."
  echo "  To show the demo right now, open preview/dashboard_preview.html."
  exit 1
fi

echo "Starting the dashboard..."
echo
"$VPY" run_demo.py
