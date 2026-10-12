"""THE VOID CROSSHAIR: controller, tray icon, command handling and start-up."""

from __future__ import annotations

import sys
from importlib.resources import files

from void_crosshair import APP_ID, APP_NAME, CLI_NAME, __version__, config, control, desktop

USAGE = f"""{APP_NAME} {__version__}: a crosshair overlay for any game or screen.

Usage:
  {CLI_NAME}                 start (or open the settings of the running copy)
  {CLI_NAME} COMMAND         control the running copy:
{{commands}}
Options:
  --background            start without opening the settings window
  --wayland / --x11       force the display backend (default: XWayland on Wayland)
  --version, --help
"""


def usage() -> str:
    width = max(len(c) for c in control.COMMANDS)
    rows = "\n".join(f"      {c.ljust(width)}  {d}" for c, d in control.COMMANDS.items())
    return USAGE.format(commands=rows)


def app_icon():
    from PySide6.QtGui import QIcon

    return QIcon(str(files("void_crosshair").joinpath("assets", f"{APP_ID}.svg")))


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if "--version" in argv:
        print(f"{APP_NAME} {__version__}")
        return 0
    if "--help" in argv or "-h" in argv:
        print(usage())
        return 0
    command = [a for a in argv if not a.startswith("--")]
    background = "--background" in argv

    reply = control.send(command or ([] if not background else ["ping"]))
    if reply is not None:              # already running: it handled the command
        if reply.startswith("error"):
            print(reply, file=sys.stderr)
            return 1
        if reply != "ok":
            print(reply.removeprefix("ok: "))
        return 0
    if command and command[0] in ("hide", "quit", "status", "ping"):
        print(f"{APP_NAME} is not running.", file=sys.stderr)
        return 1
    # Any other command starts the app first, then applies the command.

    desktop.choose_platform(argv)
    from PySide6.QtWidgets import QApplication

    from void_crosshair.controller import Controller, Server, load_fonts, tray
    from void_crosshair.overlay import platform
    from void_crosshair.shortcuts import PortalShortcuts
    from void_crosshair.window import QSS

    app = QApplication.instance() or QApplication([sys.argv[0]])
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(APP_ID)
    app.setQuitOnLastWindowClosed(False)
    load_fonts()
    app.setStyleSheet(QSS)
    icon = app_icon()
    app.setWindowIcon(icon)

    settings = config.load()
    settings.visible = True
    ctl = Controller(settings)
    server = Server(ctl.handle)
    if not server.listen():
        print("warning: terminal commands unavailable (could not open the control socket)",
              file=sys.stderr)
    ctl.platform = platform()
    shortcuts = PortalShortcuts()
    shortcuts.activated.connect(ctl.shortcut)
    shortcuts.released.connect(ctl.shortcut_released)
    ctl.shortcuts = shortcuts
    shortcuts.start()
    ctl.tray = tray(ctl, icon)

    if command:
        reply = ctl.handle(command)
        if reply.startswith("error"):
            print(reply, file=sys.stderr)
    elif not background and settings.open_settings_on_start:
        ctl.open_settings()
    code = app.exec()
    server.server.close()
    return code


def gui_main() -> int:
    return main()


if __name__ == "__main__":
    sys.exit(main())
