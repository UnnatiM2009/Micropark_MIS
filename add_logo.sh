#!/usr/bin/env bash
# Install a logo:  ./add_logo.sh /path/to/logo.png
cd "$(dirname "$0")" || exit 1
if [ -x venv/bin/python ]; then
  venv/bin/python scripts/add_logo.py "$@"
else
  python3 scripts/add_logo.py "$@"
fi
