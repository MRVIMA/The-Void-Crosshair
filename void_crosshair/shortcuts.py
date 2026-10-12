"""Global shortcuts through the desktop portal (org.freedesktop.portal.GlobalShortcuts).

This is the Wayland-friendly way: the desktop (KDE Plasma 6, GNOME 48+, Hyprland, ...)
owns the keys, asks the user once, and tells us when a shortcut fires. Nothing here reads
the keyboard. Where the portal is missing, the same actions work as terminal commands
(`void-crosshair toggle`) that can be bound in any desktop's shortcut settings.
"""

from __future__ import annotations

import contextlib
import secrets
import threading
from queue import Empty, Queue

from PySide6.QtCore import QObject, Signal

from void_crosshair import APP_ID

# (id, description, preferred trigger). The desktop may let the user pick other keys.
SHORTCUTS = [
    ("toggle", "Show / hide the crosshair", "CTRL+ALT+SHIFT+H"),
    ("hold_hide", "Hide while held (e.g. for scopes)", "CTRL+ALT+SHIFT+J"),
    ("settings", "Open settings", "CTRL+ALT+SHIFT+X"),
    ("next", "Next crosshair style", "CTRL+ALT+SHIFT+N"),
    ("prev", "Previous crosshair style", "CTRL+ALT+SHIFT+B"),
    ("center", "Back to the screen centre", "CTRL+ALT+SHIFT+C"),
    ("screen", "Move to the next display", "CTRL+ALT+SHIFT+M"),
    ("up", "Nudge up 1 px", "CTRL+ALT+SHIFT+Up"),
    ("down", "Nudge down 1 px", "CTRL+ALT+SHIFT+Down"),
    ("left", "Nudge left 1 px", "CTRL+ALT+SHIFT+Left"),
    ("right", "Nudge right 1 px", "CTRL+ALT+SHIFT+Right"),
]

PORTAL_PATH = "/org/freedesktop/portal/desktop"
PORTAL_BUS = "org.freedesktop.portal.Desktop"
IFACE = "org.freedesktop.portal.GlobalShortcuts"


class PortalShortcuts(QObject):
    """Binds SHORTCUTS in a background thread; emits activated(id) / released(id)."""

    activated = Signal(str)
    released = Signal(str)
    status = Signal(bool, str)   # (working, message)

    def __init__(self) -> None:
        super().__init__()
        self.router = None
        self.session = ""
        self.bound: dict[str, str] = {}   # id -> trigger description from the desktop
        self._stop = threading.Event()

    def start(self) -> None:
        threading.Thread(target=self._run, name="portal-shortcuts", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        if self.router is not None:
            with contextlib.suppress(Exception):
                self.router.close()

    def configure(self) -> bool:
        """Open the desktop's own dialog to change the keys (portal version 2)."""
        if self.router is None or not self.session:
            return False
        from jeepney import DBusAddress, new_method_call

        portal = DBusAddress(PORTAL_PATH, bus_name=PORTAL_BUS, interface=IFACE)
        try:
            msg = new_method_call(portal, "ConfigureShortcuts", "osa{sv}",
                                  (self.session, "", {}))
            self.router.send_and_get_reply(msg, timeout=5)
            return True
        except Exception:
            return False

    # -- background thread --------------------------------------------------------------
    def _run(self) -> None:
        try:
            self._bind_and_listen()
        except ImportError:
            self.status.emit(False, "Python package 'jeepney' is missing; use terminal commands.")
        except Exception as exc:
            if not self._stop.is_set():
                self.status.emit(False, f"Desktop portal unavailable ({type(exc).__name__}: "
                                        f"{exc}). Use terminal commands instead.")

    def _request(self, router, portal, method: str, signature: str, body: tuple,
                 timeout: float) -> dict:
        """Call a portal method that answers through a Request object's Response signal."""
        from jeepney import MatchRule, message_bus, new_method_call
        from jeepney.io.threading import Proxy

        token = "voidcrosshair_" + secrets.token_hex(4)
        sender = router.unique_name[1:].replace(".", "_")
        path = f"{PORTAL_PATH}/request/{sender}/{token}"
        rule = MatchRule(type="signal", interface="org.freedesktop.portal.Request",
                         member="Response", path=path)
        Proxy(message_bus, router).AddMatch(rule)
        options = body[-1]
        options["handle_token"] = ("s", token)
        with router.filter(rule) as queue:
            router.send_and_get_reply(new_method_call(portal, method, signature, body),
                                      timeout=10)
            code, results = queue.get(timeout=timeout).body
        if code != 0:
            raise RuntimeError("cancelled" if code == 1 else f"{method} failed ({code})")
        return results

    def _bind_and_listen(self) -> None:
        from jeepney import DBusAddress, HeaderFields, MatchRule, message_bus, new_method_call
        from jeepney.io.threading import Proxy, open_dbus_router

        self.router = router = open_dbus_router(bus="SESSION")
        # Tell the portal who we are (needed for unsandboxed apps; older portals lack it).
        try:
            registry = DBusAddress(PORTAL_PATH, bus_name=PORTAL_BUS,
                                   interface="org.freedesktop.host.portal.Registry")
            router.send_and_get_reply(new_method_call(registry, "Register", "sa{sv}",
                                                      (APP_ID, {})), timeout=5)
        except Exception:
            pass
        portal = DBusAddress(PORTAL_PATH, bus_name=PORTAL_BUS, interface=IFACE)
        session_token = "voidcrosshair_" + secrets.token_hex(4)
        created = self._request(router, portal, "CreateSession", "a{sv}",
                                ({"session_handle_token": ("s", session_token)},), timeout=30)
        self.session = created["session_handle"][1]
        wanted = [(sid, {"description": ("s", desc), "preferred_trigger": ("s", trigger)})
                  for sid, desc, trigger in SHORTCUTS]
        # The desktop may show a confirmation dialog here, so allow the user time.
        bound = self._request(router, portal, "BindShortcuts", "oa(sa{sv})sa{sv}",
                              (self.session, wanted, "", {}), timeout=300)
        for sid, props in bound.get("shortcuts", ("", []))[1]:
            self.bound[sid] = props.get("trigger_description", ("s", ""))[1]
        self.status.emit(True, "Global shortcuts active (desktop portal).")

        events: Queue = Queue(maxsize=64)
        handles = []   # keep the filters registered while we listen
        for member in ("Activated", "Deactivated"):
            rule = MatchRule(type="signal", interface=IFACE, member=member, path=PORTAL_PATH)
            Proxy(message_bus, router).AddMatch(rule)
            handles.append(router.filter(rule, queue=events))
        while not self._stop.is_set():
            try:
                msg = events.get(timeout=1)
            except Empty:
                continue
            session, shortcut_id = msg.body[0], msg.body[1]
            if session != self.session:
                continue
            if msg.header.fields.get(HeaderFields.member) == "Activated":
                self.activated.emit(shortcut_id)
            else:
                self.released.emit(shortcut_id)
