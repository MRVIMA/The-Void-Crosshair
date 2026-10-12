"""Desktop integration: start with the system (XDG autostart) and display-server choice."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from void_crosshair import APP_ID, APP_NAME


def launcher() -> list[str]:
    """The command that starts this copy of the app (AppImage, frozen build or Python)."""
    if os.environ.get("APPIMAGE"):
        return [os.environ["APPIMAGE"]]
    if getattr(sys, "frozen", False):
        return [sys.executable]
    found = shutil.which("the-void-crosshair")
    if found:
        return [found]
    return [sys.executable, "-m", "void_crosshair"]


def _exec_line(args: list[str]) -> str:
    # Desktop-entry Exec quoting: double quotes around arguments with spaces.
    return " ".join(f'"{a}"' if any(c in a for c in ' \t"\'\\$`') else a for a in args)


def autostart_file() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "autostart" / f"{APP_ID}.desktop"


def autostart_enabled() -> bool:
    return autostart_file().is_file()


def set_autostart(on: bool) -> None:
    path = autostart_file()
    if not on:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        "Comment=Crosshair overlay\n"
        f"Exec={_exec_line([*launcher(), '--background'])}\n"
        f"Icon={APP_ID}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def choose_platform(argv: list[str], env: dict | None = None) -> str | None:
    """Pick Qt's display backend before QApplication exists; returns what was chosen.

    On a Wayland session we run through XWayland by default: only X11 lets a window place
    itself at the screen centre and stay above fullscreen games. --wayland opts out.
    """
    env = os.environ if env is None else env
    if env.get("QT_QPA_PLATFORM"):
        return env["QT_QPA_PLATFORM"]
    if "--wayland" in argv:
        env["QT_QPA_PLATFORM"] = "wayland"
    elif "--x11" in argv:
        env["QT_QPA_PLATFORM"] = "xcb"
    elif env.get("WAYLAND_DISPLAY") and env.get("DISPLAY"):
        env["QT_QPA_PLATFORM"] = "xcb;wayland"    # native Wayland if XWayland refuses us
    return env.get("QT_QPA_PLATFORM")


def describe_platform(name: str, env: dict | None = None) -> str:
    env = os.environ if env is None else env
    wayland_session = bool(env.get("WAYLAND_DISPLAY"))
    if name == "xcb" and wayland_session:
        return "Wayland session, overlay through XWayland (recommended: exact centre, above games)."
    if name == "xcb":
        return "X11 session (overlay above all windows)."
    if name == "wayland":
        return ("Native Wayland: the desktop decides window placement, so the crosshair may "
                "not stay above fullscreen games. Remove --wayland to use XWayland.")
    return f"Qt platform: {name}"
