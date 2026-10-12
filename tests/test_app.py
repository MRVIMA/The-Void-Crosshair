"""Controller, overlay windows and the settings window (Qt offscreen platform)."""

import pytest

from void_crosshair import config


@pytest.fixture
def ctl(qapp, tmp_path):
    from void_crosshair.controller import Controller

    c = Controller(config.Settings(), path=tmp_path / "settings.json")
    yield c
    c.close()


def test_overlay_is_centred_and_click_through(ctl):
    from PySide6.QtCore import QRect, Qt

    from void_crosshair import render
    from void_crosshair.overlay import target_rect

    s = config.Settings(size=40, offset_x=5, offset_y=-3)
    half = render.extent(s)
    r = target_rect(s, QRect(1920, 0, 2560, 1440))
    assert r.center().x() + 1 == 1920 + 1280 + 5 and r.width() == half * 2
    assert r.y() + half == 720 - 3
    o = ctl.overlays[0]
    assert o.windowFlags() & Qt.WindowType.WindowTransparentForInput
    assert o.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert o.isVisible()


def test_commands(ctl):
    assert ctl.handle(["toggle"]) == "ok" and not ctl.s.visible
    assert not ctl.overlays[0].isVisible()
    assert ctl.handle(["show"]) == "ok" and ctl.overlays[0].isVisible()
    assert ctl.handle(["set", "size", "50"]) == "ok" and ctl.s.size == 50
    assert ctl.handle(["set", "outline-width", "3"]) == "ok" and ctl.s.outline_width == 3
    assert ctl.handle(["set", "color", "purple"]).startswith("error")
    assert ctl.handle(["set", "presets", "x"]).startswith("error")
    assert ctl.handle(["move", "4", "-2"]) == "ok" and (ctl.s.offset_x, ctl.s.offset_y) == (4, -2)
    assert ctl.handle(["move", "a", "b"]).startswith("error")
    assert ctl.handle(["center"]) == "ok" and (ctl.s.offset_x, ctl.s.offset_y) == (0, 0)
    assert ctl.handle(["preset", "the", "void"]) == "ok" and ctl.s.color == "#D90429"
    assert ctl.handle(["preset", "nope"]).startswith("error")
    assert ctl.handle(["up"]) == "ok" and ctl.s.offset_y == -1
    assert ctl.handle(["frobnicate"]).startswith("error")
    assert '"style"' in ctl.handle(["status"])


def test_cycle_skips_image_without_a_file(ctl):
    ctl.update(style=config.STYLES[-2])
    ctl.cycle(1)
    assert ctl.s.style == config.STYLES[0]
    ctl.cycle(-1)
    assert ctl.s.style == config.STYLES[-2]
    ctl.update(image="/some/file.png")
    ctl.cycle(1)
    assert ctl.s.style == "image"


def test_presets_and_saving(ctl, tmp_path):
    ctl.update(style="dot", color="#123456")
    ctl.save_preset("Mine")
    ctl.update(style="cross")
    assert ctl.apply_preset("mine") and ctl.s.style == "dot"
    ctl.save_now()
    saved = config.load(tmp_path / "settings.json")
    assert saved.presets["Mine"]["color"] == "#123456"
    ctl.delete_preset("Mine")
    assert "Mine" not in ctl.presets()


def test_all_screens_and_hold_hide(ctl, qapp):
    ctl.update(all_screens=True)
    assert len(ctl.overlays) == len(qapp.screens())
    ctl.shortcut("hold_hide")
    assert not ctl.overlays[0].isVisible() and ctl.s.visible
    ctl.shortcut_released("hold_hide")
    assert ctl.overlays[0].isVisible()


def test_settings_window_live_updates(ctl, qapp):
    ctl.open_settings()
    w = ctl.window
    assert w.isVisible()
    slider = w.controls["size"][0]
    slider.setValue(80)
    assert ctl.s.size == 80
    ctl.update(thickness=5)
    assert w.controls["thickness"][0].value() == 5
    ctl.handle(["toggle"])
    assert w.toggle_btn.text() == "SHOW CROSSHAIR"
    gallery = [w.gallery.item(i).data(256) for i in range(w.gallery.count())]
    assert gallery == list(config.STYLES)
    w.close()
    assert not w.isVisible()          # closing only hides; the crosshair keeps running
    assert ctl.overlays
