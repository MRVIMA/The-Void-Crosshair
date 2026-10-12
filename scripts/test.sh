#!/usr/bin/env bash
# Lint + tests. No network, no real desktop: Qt runs offscreen and the portal is not contacted.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
.venv/bin/ruff check void_crosshair tests scripts
QT_QPA_PLATFORM=offscreen DBUS_SESSION_BUS_ADDRESS=unix:path=/nonexistent .venv/bin/python -m pytest "$@"
