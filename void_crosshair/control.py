"""One running copy; later launches pass their command to it over a local socket.

No Qt in here, so terminal commands start fast.
"""

from __future__ import annotations

import json
import os
import socket

from void_crosshair import APP_SLUG

COMMANDS = {
    "show": "show the crosshair",
    "hide": "hide the crosshair",
    "toggle": "show / hide",
    "settings": "open the settings window",
    "next": "next crosshair style",
    "prev": "previous crosshair style",
    "preset NAME": "apply a preset",
    "center": "remove the offset (back to the screen centre)",
    "move DX DY": "nudge by pixels, e.g. move 0 -2",
    "screen": "move to the next display",
    "set KEY VALUE": "change one setting, e.g. set color FF0000 or set size 30",
    "status": "print the current settings as JSON",
    "quit": "close THE VOID CROSSHAIR",
}


def server_name() -> str:
    """Socket path: per-user runtime dir (private to the user) when there is one."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime and os.path.isdir(runtime):
        path = os.path.join(runtime, f"{APP_SLUG}.sock")
        if len(path.encode()) < 100:     # Unix socket paths are limited to ~107 bytes
            return path
    return f"/tmp/{APP_SLUG}-{os.getuid()}.sock"


def send(args: list[str], timeout: float = 2.0) -> str | None:
    """Send a command to the running copy; returns its reply, or None if none is running.

    Plain sockets, no Qt: a keyboard shortcut bound to `void-crosshair toggle` stays instant.
    """
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(server_name())
            sock.sendall((json.dumps(args) + "\n").encode())
            reply = b""
            while not reply.endswith(b"\n"):
                chunk = sock.recv(65536)
                if not chunk:
                    break
                reply += chunk
    except OSError:
        return None
    return reply.decode(errors="replace").strip()
