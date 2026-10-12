#!/usr/bin/env bash
# Create the environment (CachyOS / Arch): reuses the system's PySide6 (Qt).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if command -v pacman >/dev/null && ! pacman -Q pyside6 >/dev/null 2>&1; then
    echo "Install first:  sudo pacman -S --needed python pyside6"
    exit 1
fi
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -q -e ".[dev]"
echo "Ready. Run: bash scripts/run.sh   ·   control: .venv/bin/void-crosshair --help"
