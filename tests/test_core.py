"""Settings, rendering, desktop integration and the terminal client (no display needed
beyond Qt's offscreen platform)."""

import json
import os
import threading

import pytest

from void_crosshair import config, control, desktop


def test_clean_clamps_and_validates():
    s = config.Settings()
    assert s.update(size=9999, thickness=0, opacity="0.5", gap="x") == ["size", "thickness",
                                                                         "opacity"]
    assert (s.size, s.thickness, s.opacity, s.gap) == (256, 1, 0.5, 4)
    s.update(color="00ffaa", outline_color="#12345G", style="nope", outline="false")
    assert (s.color, s.outline_color, s.style, s.outline) == ("#00FFAA", "#000000",
                                                              "cross_dot", False)
    with pytest.raises(KeyError):
        s.update(colour="#FFFFFF")


def test_save_load_roundtrip_and_bad_files(tmp_path):
    path = tmp_path / "settings.json"
    s = config.Settings(style="circle", size=50, presets={"Mine": {"style": "dot"}})
    config.save(s, path)
    back = config.load(path)
    assert (back.style, back.size, back.presets) == ("circle", 50, {"Mine": {"style": "dot"}})
    path.write_text(json.dumps({"size": -5, "unknown": 1, "style": "x"}))
    back = config.load(path)
    assert (back.size, back.style) == (4, "x")
    path.write_text("{not json")
    assert config.load(path) == config.Settings()
    assert config.load(tmp_path / "missing.json") == config.Settings()


def test_presets_are_complete_looks():
    for name, values in config.BUILTIN_PRESETS.items():
        look = config.preset_look(values)
        assert set(look) == set(config.LOOK), name
        assert look["style"] in config.STYLES
    assert "offset_x" not in config.preset_look({"offset_x": 5, "size": 10})


def test_choose_platform():
    env = {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}
    assert desktop.choose_platform([], env) == "xcb;wayland"
    assert desktop.choose_platform(["--x11"], {"WAYLAND_DISPLAY": "w"}) == "xcb"
    env = {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}
    assert desktop.choose_platform(["--wayland"], env) == "wayland"
    assert desktop.choose_platform([], {"WAYLAND_DISPLAY": "wayland-0"}) is None
    assert desktop.choose_platform([], {"QT_QPA_PLATFORM": "offscreen",
                                        "DISPLAY": ":0", "WAYLAND_DISPLAY": "w"}) == "offscreen"


def test_autostart_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPIMAGE", "/home/me/My Apps/THE-VOID-CROSSHAIR.AppImage")
    assert not desktop.autostart_enabled()
    desktop.set_autostart(True)
    text = desktop.autostart_file().read_text()
    assert 'Exec="/home/me/My Apps/THE-VOID-CROSSHAIR.AppImage" --background' in text
    assert desktop.autostart_enabled()
    desktop.set_autostart(False)
    assert not desktop.autostart_enabled()


def test_socket_path_stays_short(monkeypatch, tmp_path):
    long_dir = tmp_path / ("x" * 120)
    long_dir.mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(long_dir))
    assert control.server_name().startswith("/tmp/")
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/nonexistent-dir")
    assert control.server_name() == f"/tmp/the-void-crosshair-{os.getuid()}.sock"


def test_send_without_running_copy(monkeypatch, short_runtime):
    assert control.send(["toggle"]) is None


def test_cli_when_not_running(short_runtime, capsys):
    from void_crosshair.app import main

    assert main(["--version"]) == 0
    assert "1.0.0" in capsys.readouterr().out
    assert main(["--help"]) == 0
    assert "move DX DY" in capsys.readouterr().out
    assert main(["status"]) == 1
    assert "not running" in capsys.readouterr().err


# -- rendering --------------------------------------------------------------------------
def _opaque(img, x0, y0, x1, y1):
    return sum(img.pixelColor(x, y).alpha() > 0 for x in range(x0, x1) for y in range(y0, y1))


@pytest.mark.parametrize("style", [s for s in config.STYLES if s != "image"])
def test_every_style_draws_inside_its_extent(qapp, style):
    from void_crosshair import render

    s = config.Settings(style=style, size=40, thickness=3, gap=4, dot=2, rotation=30)
    side = render.extent(s) * 2
    img = render.pixmap(s, side).toImage()
    total = _opaque(img, 0, 0, side, side)
    assert total > 10, "nothing drawn"
    assert _opaque(img, 1, 1, side - 1, side - 1) == total, "drawing clipped at the edge"


def test_colour_outline_and_opacity(qapp):
    from void_crosshair import render

    s = config.Settings(style="dot", dot=6, color="#00FF00", outline=True, outline_width=2,
                        outline_color="#000000")
    img = render.pixmap(s, 40).toImage()
    centre = img.pixelColor(20, 20)
    assert (centre.red(), centre.green(), centre.blue()) == (0, 255, 0)
    edge = img.pixelColor(20 + 7, 20)
    assert edge.alpha() > 0 and edge.green() < 128          # outline ring
    s.update(opacity=0.5, outline=False)
    half = render.pixmap(s, 40).toImage().pixelColor(20, 20)
    assert 100 < half.alpha() < 160


def test_ring_has_a_hole(qapp):
    from void_crosshair import render

    s = config.Settings(style="circle", size=40, thickness=2, outline=False)
    img = render.pixmap(s, 60).toImage()
    assert img.pixelColor(30, 30).alpha() == 0
    assert img.pixelColor(30 + 19, 30).alpha() > 0


def test_image_crosshair(qapp, tmp_path):
    from PySide6.QtGui import QColor, QImage

    from void_crosshair import render

    png = tmp_path / "x.png"
    src = QImage(16, 16, QImage.Format.Format_ARGB32)
    src.fill(QColor("#FFFFFF"))
    src.save(str(png))
    s = config.Settings(style="image", image=str(png), size=16, tint_image=True,
                        color="#FF0000")
    img = render.pixmap(s, 32).toImage()
    c = img.pixelColor(16, 16)
    assert (c.red(), c.green(), c.alpha()) == (255, 0, 255)
    s.update(image=str(tmp_path / "missing.png"))
    from PySide6.QtGui import QPainter, QPixmap

    pm = QPixmap(10, 10)
    p = QPainter(pm)
    assert render.paint(p, s, 5, 5) is False
    p.end()


# -- fixtures ---------------------------------------------------------------------------
@pytest.fixture
def short_runtime(monkeypatch):
    import tempfile

    d = tempfile.mkdtemp(prefix="xh", dir="/tmp")
    monkeypatch.setenv("XDG_RUNTIME_DIR", d)
    yield d


def test_socket_roundtrip(qapp, short_runtime):
    from void_crosshair.controller import Server

    server = Server(lambda args: "ok: " + "|".join(args))
    assert server.listen()
    result = {}
    t = threading.Thread(target=lambda: result.setdefault("r", control.send(["move", "0",
                                                                             "-2"])))
    t.start()
    while t.is_alive():
        qapp.processEvents()
        t.join(0.01)
    assert result["r"] == "ok: move|0|-2"
    # Let the server see the client hang up and delete its socket before it goes away.
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtNetwork import QLocalSocket

    for _ in range(50):
        qapp.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        if not server.server.findChildren(QLocalSocket):
            break
    server.server.close()
