"""The running app: overlay windows, settings, commands, shortcuts and the tray icon."""

from __future__ import annotations

import json
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QFontDatabase, QGuiApplication, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from void_crosshair import APP_NAME, config, control
from void_crosshair.overlay import Overlay


class Server(QObject):
    """Receives commands; `handler(args) -> reply` runs on the GUI thread."""

    def __init__(self, handler) -> None:
        super().__init__()
        self.handler = handler
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self._accept)

    def listen(self) -> bool:
        if self.server.listen(control.server_name()):
            return True
        QLocalServer.removeServer(control.server_name())   # stale socket from a crash
        return self.server.listen(control.server_name())

    def _accept(self) -> None:
        while self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            sock.readyRead.connect(lambda s=sock: self._read(s))
            sock.disconnected.connect(sock.deleteLater)

    def _read(self, sock: QLocalSocket) -> None:
        if not sock.canReadLine():
            return
        try:
            args = json.loads(bytes(sock.readLine().data()))
            reply = self.handler([str(a) for a in args])
        except Exception as exc:  # a bad command must never take the overlay down
            reply = f"error: {exc}"
        sock.write((reply + "\n").encode())
        sock.flush()

class Controller(QObject):
    """Owns the settings and the overlay windows; every action goes through here."""

    changed = Signal(list)          # names of settings that changed
    visibility = Signal(bool)

    def __init__(self, settings: config.Settings, path: Path | None = None,
                 persist: bool = True) -> None:
        super().__init__()
        self.s = settings
        self.path = path
        self.persist = persist
        self.held = False           # "hide while held" shortcut is down
        self.overlays: list[Overlay] = []
        self.window = None
        self.shortcuts = None
        self.tray = None
        self.platform = ""
        self._save = QTimer(self, singleShot=True, interval=400)
        self._save.timeout.connect(self.save_now)
        app = QGuiApplication.instance()
        for signal in (app.screenAdded, app.screenRemoved, app.primaryScreenChanged):
            signal.connect(self._screens_changed)
        self.rebuild()

    def _screens_changed(self, *_args) -> None:
        # A removed screen is still listed while its signal runs, so wait a moment.
        QTimer.singleShot(0, self.rebuild)

    def close(self) -> None:
        """Remove every window and stop reacting to the desktop (quit, tests)."""
        app = QGuiApplication.instance()
        for signal in (app.screenAdded, app.screenRemoved, app.primaryScreenChanged):
            signal.disconnect(self._screens_changed)
        for o in self.overlays:
            o.close()
            o.deleteLater()
        self.overlays = []
        if self.window is not None:
            self.window.hide()
            self.window.deleteLater()
            self.window = None

    # -- overlays ------------------------------------------------------------------
    def screens(self) -> list:
        all_screens = QGuiApplication.screens()
        if self.s.all_screens:
            return all_screens
        for sc in all_screens:
            if sc.name() == self.s.screen:
                return [sc]
        return [QGuiApplication.primaryScreen()]

    def shown(self) -> bool:
        return self.s.visible and not self.held

    def rebuild(self) -> None:
        for o in self.overlays:
            o.close()
            o.deleteLater()
        self.overlays = [Overlay(self.s, sc) for sc in self.screens() if sc is not None]
        self.refresh()

    def refresh(self) -> None:
        for o in self.overlays:
            o.place(o.target)
            o.setVisible(self.shown())
        self.visibility.emit(self.s.visible)

    def image_ok(self) -> bool:
        return all(o.image_ok for o in self.overlays)

    # -- changes -------------------------------------------------------------------
    def update(self, **values) -> list[str]:
        names = self.s.update(**values)
        if not names:
            return names
        if {"screen", "all_screens"} & set(names):
            self.rebuild()
        else:
            self.refresh()
        if set(names) - {"visible"}:
            self._save.start()
        self.changed.emit(names)
        return names

    def save_now(self) -> None:
        if self.persist:
            config.save(self.s, self.path)

    def presets(self) -> dict[str, dict]:
        return {**config.BUILTIN_PRESETS, **self.s.presets}

    def apply_preset(self, name: str) -> bool:
        for key, look in self.presets().items():
            if key.lower() == name.lower():
                self.update(**config.preset_look(look))
                return True
        return False

    def save_preset(self, name: str) -> None:
        presets = dict(self.s.presets)
        presets[name] = self.s.look()
        self.update(presets=presets)

    def delete_preset(self, name: str) -> None:
        presets = {k: v for k, v in self.s.presets.items() if k != name}
        self.update(presets=presets)

    def cycle(self, step: int) -> None:
        styles = [s for s in config.STYLES if s != "image" or self.s.image]
        i = styles.index(self.s.style) if self.s.style in styles else 0
        self.update(style=styles[(i + step) % len(styles)])

    def next_screen(self) -> str:
        names = [sc.name() for sc in QGuiApplication.screens()]
        current = self.screens()[0].name() if not self.s.all_screens else ""
        i = names.index(current) if current in names else -1
        name = names[(i + 1) % len(names)]
        self.update(screen=name, all_screens=False)
        return name

    def move(self, dx: int, dy: int) -> None:
        self.update(offset_x=self.s.offset_x + dx, offset_y=self.s.offset_y + dy)

    # -- commands (terminal, tray, shortcuts) --------------------------------------
    def handle(self, args: list[str]) -> str:
        if not args:
            self.open_settings()
            return "ok"
        cmd, rest = args[0].lower(), args[1:]
        simple = {
            "show": lambda: self.update(visible=True),
            "hide": lambda: self.update(visible=False),
            "toggle": lambda: self.update(visible=not self.s.visible),
            "settings": self.open_settings,
            "next": lambda: self.cycle(1),
            "prev": lambda: self.cycle(-1),
            "center": lambda: self.update(offset_x=0, offset_y=0),
            "up": lambda: self.move(0, -1),
            "down": lambda: self.move(0, 1),
            "left": lambda: self.move(-1, 0),
            "right": lambda: self.move(1, 0),
            "quit": lambda: QTimer.singleShot(50, self.quit),
            "ping": lambda: None,
        }
        if cmd in simple and not rest:
            simple[cmd]()
            return "ok"
        if cmd == "screen" and not rest:
            return f"ok: {self.next_screen() or 'display'}"
        if cmd == "status":
            return json.dumps(asdict(self.s), indent=2)
        if cmd == "preset" and rest:
            name = " ".join(rest)
            return "ok" if self.apply_preset(name) else \
                f"error: no preset {name!r}; have: {', '.join(self.presets())}"
        if cmd == "move" and len(rest) == 2:
            try:
                self.move(int(rest[0]), int(rest[1]))
            except ValueError:
                return "error: move needs two whole numbers, e.g. move 0 -2"
            return "ok"
        if cmd == "set" and len(rest) >= 2:
            key, value = rest[0].replace("-", "_"), " ".join(rest[1:])
            if key in ("presets",) or not hasattr(self.s, key):
                return f"error: unknown setting {rest[0]!r}"
            before = getattr(self.s, key)
            self.update(**{key: value})
            if getattr(self.s, key) == before and str(before) != value:
                return f"error: {value!r} is not a valid {key}"
            return "ok"
        return f"error: unknown command {' '.join(args)!r} (try --help)"

    def shortcut(self, sid: str) -> None:
        if sid == "hold_hide":
            self.held = True
            self.refresh()
        else:
            self.handle([sid])

    def shortcut_released(self, sid: str) -> None:
        if sid == "hold_hide":
            self.held = False
            self.refresh()

    # -- windows -------------------------------------------------------------------
    def open_settings(self) -> None:
        if self.window is None:
            from void_crosshair.window import SettingsWindow

            self.window = SettingsWindow(self)
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def quit(self) -> None:
        self._save.stop()
        self.save_now()
        if self.shortcuts is not None:
            self.shortcuts.stop()
        self.close()
        QApplication.instance().quit()


def tray(ctl: Controller, icon: QIcon) -> QSystemTrayIcon | None:
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    t = QSystemTrayIcon(icon)
    t.setToolTip(APP_NAME)
    menu = QMenu()
    toggle = QAction("Hide crosshair", menu)
    toggle.triggered.connect(lambda: ctl.handle(["toggle"]))
    ctl.visibility.connect(lambda v: toggle.setText("Hide crosshair" if v else
                                                    "Show crosshair"))
    menu.addAction(toggle)
    menu.addAction("Next style", lambda: ctl.cycle(1))
    menu.addAction("Previous style", lambda: ctl.cycle(-1))
    presets = menu.addMenu("Presets")

    def fill_presets() -> None:
        presets.clear()
        for name in ctl.presets():
            presets.addAction(name, lambda n=name: ctl.apply_preset(n))

    presets.aboutToShow.connect(fill_presets)
    menu.addAction("Back to centre", lambda: ctl.handle(["center"]))
    menu.addAction("Next display", ctl.next_screen)
    menu.addSeparator()
    menu.addAction("Settings…", ctl.open_settings)
    menu.addAction("Quit", ctl.quit)
    t.setContextMenu(menu)
    t.activated.connect(lambda reason: ctl.open_settings()
                        if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    t.show()
    return t

def load_fonts() -> None:
    for f in files("void_crosshair").joinpath("assets", "fonts").iterdir():
        if f.name.endswith(".ttf"):
            QFontDatabase.addApplicationFont(str(f))

