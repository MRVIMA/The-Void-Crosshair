"""PyInstaller entry point: the app; any arguments are commands (`toggle`, `quit`, ...)."""

import sys

from void_crosshair.app import main

if __name__ == "__main__":
    sys.exit(main())
