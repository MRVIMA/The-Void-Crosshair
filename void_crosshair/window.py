"""Settings window (PySide6, THE VOID theme). Every change applies live."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from void_crosshair import APP_NAME, CLI_NAME, __version__, config, desktop, render
from void_crosshair.shortcuts import SHORTCUTS

BG, PANEL, BORDER, FG, MUTED = "#08090D", "#111318", "#292D36", "#F2F2F2", "#9599A4"
CRIMSON, GREEN, AMBER = "#D90429", "#3DDC97", "#FFB020"
SWATCHES = ["#D90429", "#FF2D55", "#00FF66", "#3DDC97", "#00FFFF", "#2D9CFF", "#FFD400",
            "#FF8A00", "#FF00FF", "#FFFFFF", "#000000"]

QSS = f"""
QWidget {{ background: {BG}; color: {FG}; font-family: Inter; font-size: 10pt; }}
QLabel#title {{ font-family: Rajdhani; font-size: 24pt; font-weight: 700; letter-spacing: 2px; }}
QLabel#subtitle, QLabel#muted {{ color: {MUTED}; }}
QLabel#section {{ font-family: Rajdhani; font-size: 12pt; font-weight: 700; letter-spacing: 1px;
                  color: {MUTED}; }}
QLabel#value {{ font-family: 'JetBrains Mono'; color: {MUTED}; min-width: 44px; }}
QLabel#mono, QLabel#cmd {{ font-family: 'JetBrains Mono'; font-size: 9pt; }}
QFrame#panel {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 4px; }}
QFrame#panel QLabel, QFrame#panel QCheckBox {{ background: transparent; }}
QPushButton {{ background: {PANEL}; border: 1px solid {BORDER}; padding: 7px 14px;
               font-family: Rajdhani; font-size: 11pt; font-weight: 700; letter-spacing: 1px; }}
QPushButton:hover {{ border-color: {CRIMSON}; }}
QPushButton:checked {{ border-color: {CRIMSON}; background: #3A0410; }}
QPushButton#primary {{ background: {CRIMSON}; border-color: {CRIMSON}; }}
QPushButton#swatch {{ padding: 0; min-width: 22px; max-width: 22px; min-height: 22px;
                      max-height: 22px; border-radius: 11px; }}
QPushButton#pad {{ min-width: 34px; max-width: 34px; padding: 6px 0; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; background: {PANEL}; top: -1px; }}
QTabWidget::pane > QWidget, QTabWidget QWidget#tab {{ background: {PANEL}; }}
QTabWidget#tabs QLabel, QTabWidget#tabs QCheckBox {{ background: transparent; }}
QTabBar::tab {{ background: {BG}; color: {MUTED}; padding: 8px 14px; border: 1px solid {BORDER};
                border-bottom: none; font-family: Rajdhani; font-size: 11pt; font-weight: 700;
                letter-spacing: 1px; }}
QTabBar::tab:selected {{ color: {FG}; background: {PANEL}; border-top: 2px solid {CRIMSON}; }}
QListWidget {{ background: {PANEL}; border: 1px solid {BORDER}; }}
QListWidget::item {{ padding: 4px; }}
QListWidget::item:selected {{ background: #3A0410; border: 1px solid {CRIMSON}; }}
QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {CRIMSON}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {FG}; width: 14px; margin: -6px 0; border-radius: 7px; }}
QSpinBox, QComboBox {{ background: {BG}; border: 1px solid {BORDER}; padding: 5px 8px; }}
QSpinBox:focus, QComboBox:focus {{ border-color: {CRIMSON}; }}
QComboBox QAbstractItemView {{ background: {PANEL}; selection-background-color: #3A0410; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {BORDER}; background: {BG}; }}
QCheckBox::indicator:checked {{ background: {CRIMSON}; border-color: {CRIMSON}; }}
QScrollBar:vertical {{ background: {PANEL}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 28px; border-radius: 5px; }}
QScrollBar::handle:vertical:hover {{ background: {CRIMSON}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QToolTip {{ background: {PANEL}; color: {FG}; border: 1px solid {BORDER}; }}
"""


class Preview(QWidget):
    """The crosshair on a sample background, at 1x, 2x or 4x."""

    BACKGROUNDS = ("Scene", "Dark", "Light")

    def __init__(self, settings: config.Settings) -> None:
        super().__init__()
        self.s = settings
        self.zoom = 1
        self.background = "Scene"
        self.setMinimumSize(300, 220)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        r = QRectF(self.rect())
        if self.background == "Scene":
            sky = QLinearGradient(0, 0, 0, r.height())
            sky.setColorAt(0, QColor("#4A6378"))
            sky.setColorAt(0.55, QColor("#A9B4A0"))
            sky.setColorAt(0.56, QColor("#5C5A44"))
            sky.setColorAt(1, QColor("#2E2C22"))
            p.fillRect(r, sky)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(QColor(0, 0, 0, 60), 1))
            for i in range(-6, 7):   # ground lines toward the horizon
                p.drawLine(QPointF(r.center().x() + i * 12, r.height() * 0.56),
                           QPointF(r.center().x() + i * 120, r.height()))
            p.fillRect(QRectF(r.width() * 0.62, r.height() * 0.3, 46, 90), QColor("#3B3F46"))
            p.fillRect(QRectF(r.width() * 0.18, r.height() * 0.38, 70, 64), QColor("#6E6250"))
            p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        else:
            p.fillRect(r, QColor("#111318" if self.background == "Dark" else "#E9EAEE"))
        c = r.center()
        p.translate(c)
        p.scale(self.zoom, self.zoom)
        render.paint(p, self.s, 0, 0)
        p.end()


class SettingsWindow(QWidget):
    def __init__(self, ctl) -> None:
        super().__init__()
        self.ctl = ctl
        self.s = ctl.s
        self._syncing = False
        self.setWindowTitle(APP_NAME)
        self.resize(980, 660)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(QLabel(APP_NAME, objectName="title"))
        titles.addWidget(QLabel("Crosshair overlay for any game or screen · Linux native",
                                objectName="subtitle"))
        header.addLayout(titles, 1)
        self.toggle_btn = QPushButton(objectName="primary")
        self.toggle_btn.clicked.connect(lambda: ctl.handle(["toggle"]))
        header.addWidget(self.toggle_btn)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        root.addLayout(body, 1)

        # Left: preview + style gallery
        left = QVBoxLayout()
        self.preview = Preview(self.s)
        left.addWidget(self.preview, 3)
        tools = QHBoxLayout()
        self.bg_group = QButtonGroup(self)
        for name in Preview.BACKGROUNDS:
            b = QPushButton(name.upper(), checkable=True, checked=name == "Scene")
            b.clicked.connect(lambda _c, n=name: self._preview(background=n))
            self.bg_group.addButton(b)
            tools.addWidget(b)
        tools.addStretch(1)
        self.zoom_group = QButtonGroup(self)
        for z in (1, 2, 4):
            b = QPushButton(f"{z}×", checkable=True, checked=z == 1)
            b.clicked.connect(lambda _c, z=z: self._preview(zoom=z))
            self.zoom_group.addButton(b)
            tools.addWidget(b)
        left.addLayout(tools)
        left.addWidget(QLabel("STYLE", objectName="section"))
        self.gallery = QListWidget()
        self.gallery.setViewMode(QListWidget.ViewMode.IconMode)
        self.gallery.setIconSize(QSize(52, 52))
        self.gallery.setGridSize(QSize(104, 84))
        self.gallery.setMovement(QListWidget.Movement.Static)
        self.gallery.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.gallery.setWordWrap(True)
        self.gallery.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.gallery.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for style in config.STYLES:
            item = QListWidgetItem(config.STYLE_NAMES[style])
            item.setData(Qt.ItemDataRole.UserRole, style)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.gallery.addItem(item)
        self.gallery.itemClicked.connect(self._pick_style)
        left.addWidget(self.gallery, 2)
        body.addLayout(left, 5)

        # Right: tabs
        self.tabs = QTabWidget(objectName="tabs")
        self.tabs.addTab(self._look_tab(), "LOOK")
        self.tabs.addTab(self._position_tab(), "POSITION")
        self.tabs.addTab(self._presets_tab(), "PRESETS")
        self.tabs.addTab(self._system_tab(), "SHORTCUTS && SYSTEM")
        self.tabs.addTab(self._about_tab(), "ABOUT")
        body.addWidget(self.tabs, 6)

        footer = QHBoxLayout()
        self.status = QLabel(objectName="muted")
        footer.addWidget(self.status, 1)
        reset = QPushButton("RESET LOOK")
        reset.clicked.connect(lambda: ctl.update(**config.Settings().look()))
        footer.addWidget(reset)
        quit_btn = QPushButton("QUIT")
        quit_btn.setToolTip("Close the crosshair too. Closing this window keeps it on screen.")
        quit_btn.clicked.connect(ctl.quit)
        footer.addWidget(quit_btn)
        root.addLayout(footer)

        ctl.changed.connect(self.sync)
        ctl.visibility.connect(lambda _v: self._sync_toggle())
        if ctl.shortcuts is not None:
            ctl.shortcuts.status.connect(self._shortcut_status)
        self.sync(None)
        self.status.setText("Closing this window keeps the crosshair on screen "
                            "(quit from the tray icon or QUIT).")

    # -- building blocks -----------------------------------------------------------------
    def _slider(self, form: QFormLayout, label: str, key: str, lo: int, hi: int,
                scale: float = 1, suffix: str = "px") -> None:
        row = QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(lo, hi)
        value = QLabel(objectName="value")
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def moved(v: int) -> None:
            value.setText(f"{v}{suffix}" if scale == 1 else f"{round(v * scale * 100)}%")
            if not self._syncing:
                self.ctl.update(**{key: v * scale})

        slider.valueChanged.connect(moved)
        row.addWidget(slider, 1)
        row.addWidget(value)
        form.addRow(label, row)
        self.controls[key] = (slider, scale, moved)

    def _color_row(self, key: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(5)
        for color in SWATCHES:
            b = QPushButton(objectName="swatch")
            b.setStyleSheet(f"background: {color};")
            b.setToolTip(color)
            b.clicked.connect(lambda _c, c=color: self.ctl.update(**{key: c}))
            row.addWidget(b)
        pick = QPushButton("…")
        pick.setToolTip("Any colour")
        pick.clicked.connect(lambda: self._pick_color(key))
        row.addWidget(pick)
        row.addStretch(1)
        return row

    def _tab(self) -> tuple[QWidget, QVBoxLayout]:
        w = QWidget(objectName="tab")
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        return w, v

    def _look_tab(self) -> QWidget:
        w, v = self._tab()
        self.controls: dict = {}
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setVerticalSpacing(10)
        form.addRow("Colour", self._color_row("color"))
        self.color_label = QLabel(objectName="mono")
        form.addRow("", self.color_label)
        for label, key in (("Size", "size"), ("Thickness", "thickness"), ("Gap", "gap"),
                           ("Centre dot", "dot")):
            self._slider(form, label, key, *config.RANGES[key])
        self._slider(form, "Opacity", "opacity", 5, 100, scale=0.01)
        self._slider(form, "Rotation", "rotation", *config.RANGES["rotation"], suffix="°")
        self.outline = QCheckBox("Outline (stays visible on any background)")
        self.outline.toggled.connect(lambda on: self._syncing or self.ctl.update(outline=on))
        form.addRow("", self.outline)
        self._slider(form, "Outline width", "outline_width", *config.RANGES["outline_width"])
        form.addRow("Outline colour", self._color_row("outline_color"))
        v.addLayout(form)
        v.addWidget(QLabel("IMAGE CROSSHAIR", objectName="section"))
        img = QHBoxLayout()
        choose = QPushButton("CHOOSE IMAGE…")
        choose.clicked.connect(self._choose_image)
        img.addWidget(choose)
        self.tint = QCheckBox("Tint with colour")
        self.tint.toggled.connect(lambda on: self._syncing or self.ctl.update(tint_image=on))
        img.addWidget(self.tint)
        img.addStretch(1)
        v.addLayout(img)
        self.image_label = QLabel(objectName="muted")
        self.image_label.setWordWrap(True)
        v.addWidget(self.image_label)
        v.addStretch(1)
        return w

    def _position_tab(self) -> QWidget:
        w, v = self._tab()
        form = QFormLayout()
        form.setVerticalSpacing(10)
        self.screen_box = QComboBox()
        self.screen_box.activated.connect(self._pick_screen)
        form.addRow("Display", self.screen_box)
        self.offset_x = QSpinBox(minimum=-4000, maximum=4000, suffix=" px")
        self.offset_y = QSpinBox(minimum=-4000, maximum=4000, suffix=" px")
        self.offset_x.valueChanged.connect(
            lambda x: self._syncing or self.ctl.update(offset_x=x))
        self.offset_y.valueChanged.connect(
            lambda y: self._syncing or self.ctl.update(offset_y=y))
        form.addRow("Offset X", self.offset_x)
        form.addRow("Offset Y", self.offset_y)
        v.addLayout(form)
        v.addWidget(QLabel("NUDGE", objectName="section"))
        pad = QGridLayout()
        pad.setSpacing(4)
        self.step = QComboBox()
        self.step.addItems(["1 px", "5 px", "20 px"])
        for text, r, c, dx, dy in (("↑", 0, 1, 0, -1), ("←", 1, 0, -1, 0), ("→", 1, 2, 1, 0),
                                   ("↓", 2, 1, 0, 1)):
            b = QPushButton(text, objectName="pad")
            b.setAutoRepeat(True)
            b.clicked.connect(lambda _c, dx=dx, dy=dy: self.ctl.move(dx * self._step(),
                                                                     dy * self._step()))
            pad.addWidget(b, r, c)
        centre = QPushButton("●", objectName="pad")
        centre.setToolTip("Back to the exact screen centre")
        centre.clicked.connect(lambda: self.ctl.handle(["center"]))
        pad.addWidget(centre, 1, 1)
        row = QHBoxLayout()
        row.addLayout(pad)
        row.addSpacing(16)
        row.addWidget(QLabel("Step"))
        row.addWidget(self.step)
        row.addStretch(1)
        v.addLayout(row)
        tip = QLabel("The overlay is centred on the display's exact middle pixel. Games that "
                     "draw their own centre slightly off can be matched with a 1 px nudge. "
                     "Play in borderless / windowed-fullscreen mode for the overlay to show.")
        tip.setObjectName("muted")
        tip.setWordWrap(True)
        v.addSpacing(10)
        v.addWidget(tip)
        v.addStretch(1)
        return w

    def _presets_tab(self) -> QWidget:
        w, v = self._tab()
        self.preset_list = QListWidget()
        self.preset_list.setIconSize(QSize(36, 36))
        self.preset_list.itemDoubleClicked.connect(lambda it: self.ctl.apply_preset(it.text()))
        v.addWidget(self.preset_list, 1)
        row = QHBoxLayout()
        for text, fn in (("APPLY", self._apply_preset), ("SAVE CURRENT…", self._save_preset),
                         ("DELETE", self._delete_preset)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        for text, fn in (("IMPORT…", self._import_presets), ("EXPORT…", self._export_presets)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)
        return w

    def _system_tab(self) -> QWidget:
        w, v = self._tab()
        v.addWidget(QLabel("GLOBAL SHORTCUTS", objectName="section"))
        self.shortcut_state = QLabel("Connecting to the desktop portal…", objectName="muted")
        self.shortcut_state.setWordWrap(True)
        v.addWidget(self.shortcut_state)
        self.shortcut_list = QLabel(objectName="mono")
        v.addWidget(self.shortcut_list)
        change = QPushButton("CHANGE KEYS…")
        change.setToolTip("Opens your desktop's shortcut settings for this app")
        change.clicked.connect(self._configure_shortcuts)
        row = QHBoxLayout()
        row.addWidget(change)
        row.addStretch(1)
        v.addLayout(row)
        cmds = QLabel("Any action also works from a terminal or a custom shortcut in your "
                      "desktop's settings, e.g. "
                      f"<span style='font-family:JetBrains Mono'>{CLI_NAME} toggle</span>, "
                      f"<span style='font-family:JetBrains Mono'>{CLI_NAME} preset Sniper</span>, "
                      f"<span style='font-family:JetBrains Mono'>{CLI_NAME} move 0 -1</span>. "
                      f"See <span style='font-family:JetBrains Mono'>{CLI_NAME} --help</span>.")
        cmds.setObjectName("muted")
        cmds.setWordWrap(True)
        v.addWidget(cmds)
        v.addSpacing(8)
        v.addWidget(QLabel("SYSTEM", objectName="section"))
        self.autostart = QCheckBox("Start with the system (crosshair on, settings closed)")
        self.autostart.setChecked(desktop.autostart_enabled())
        self.autostart.toggled.connect(self._set_autostart)
        v.addWidget(self.autostart)
        self.open_on_start = QCheckBox("Open this window when the app is started from the menu")
        self.open_on_start.toggled.connect(
            lambda on: self._syncing or self.ctl.update(open_settings_on_start=on))
        v.addWidget(self.open_on_start)
        info = QLabel(desktop.describe_platform(getattr(self.ctl, "platform", "")),
                      objectName="muted")
        info.setWordWrap(True)
        v.addSpacing(6)
        v.addWidget(info)
        v.addStretch(1)
        self._shortcut_status(None, "")
        return w

    def _about_tab(self) -> QWidget:
        w, v = self._tab()
        text = QLabel(
            f"<p style='font-family:Rajdhani;font-size:16pt;font-weight:700'>{APP_NAME} "
            f"{__version__}</p>"
            "<p>A <b>THE VOID</b> project by <b>THE VOID PROTOCOL</b><br>"
            "Owner of THE VOID: <b>MRVIMA</b> (alias <b>VOIDVIMA</b>)<br>"
            "<a style='color:#D90429' href='mailto:thevoidofficialprivacy@gmail.com'>"
            "thevoidofficialprivacy@gmail.com</a></p>"
            "<p>Inspired by <a style='color:#D90429' "
            "href='https://github.com/lacymorrow/crossover'>CrossOver</a> by Lacy Morrow. "
            "THE VOID CROSSHAIR is an independent rewrite for Linux (Qt instead of Electron) "
            "and isn't affiliated with CrossOver.</p>"
            "<p style='color:#9599A4'>A crosshair overlay only draws on top of the screen; it "
            "never reads or changes any game. Some competitive games or leagues have rules "
            "about overlays, so check them before ranked play.</p>"
            "<p style='color:#9599A4'>MIT License · Fonts: Rajdhani, Inter, JetBrains Mono "
            "(SIL Open Font License)</p>")
        text.setWordWrap(True)
        text.setOpenExternalLinks(True)
        text.setTextFormat(Qt.TextFormat.RichText)
        v.addWidget(text)
        v.addStretch(1)
        return w

    # -- sync from settings -------------------------------------------------------------
    def sync(self, names: list[str] | None) -> None:
        self._syncing = True
        try:
            s = self.s
            for key, (slider, scale, moved) in self.controls.items():
                slider.setValue(round(getattr(s, key) / scale))
                moved(slider.value())
            self.outline.setChecked(s.outline)
            self.tint.setChecked(s.tint_image)
            self.color_label.setText(f"{s.color}   outline {s.outline_color}")
            self.image_label.setText(s.image or "No image chosen. PNG, SVG, WebP, JPG, BMP or "
                                                "GIF; a crosshair pack folder works well.")
            self.offset_x.setValue(s.offset_x)
            self.offset_y.setValue(s.offset_y)
            self.open_on_start.setChecked(s.open_settings_on_start)
            if names is None or set(names) & set(config.LOOK) - {"style"}:
                self._refresh_icons()
            for i in range(self.gallery.count()):
                item = self.gallery.item(i)
                item.setSelected(item.data(Qt.ItemDataRole.UserRole) == s.style)
            self._refresh_screens()
            self._refresh_presets()
            self._sync_toggle()
            if s.style == "image" and s.image and not self.ctl.image_ok():
                self.status.setText(f"Couldn't load the image: {s.image}")
        finally:
            self._syncing = False
        self.preview.update()

    def _sync_toggle(self) -> None:
        self.toggle_btn.setText("HIDE CROSSHAIR" if self.s.visible else "SHOW CROSSHAIR")

    def _refresh_icons(self) -> None:
        for i in range(self.gallery.count()):
            item = self.gallery.item(i)
            look = config.Settings(**{**self.s.look(),
                                      "style": item.data(Qt.ItemDataRole.UserRole)})
            look.size = min(look.size, 44)
            look.rotation = 0 if look.style != "image" else look.rotation
            item.setIcon(QIcon(render.pixmap(look, 52, QColor(PANEL))))

    def _refresh_screens(self) -> None:
        from PySide6.QtGui import QGuiApplication

        self.screen_box.clear()
        current = self.ctl.screens()[0].name() if self.ctl.screens() else ""
        for sc in QGuiApplication.screens():
            g = sc.geometry()
            self.screen_box.addItem(f"{sc.name()}  ({g.width()}×{g.height()})", sc.name())
        self.screen_box.addItem("All displays (mirror)", "*")
        index = self.screen_box.count() - 1 if self.s.all_screens else \
            max(self.screen_box.findData(current), 0)
        self.screen_box.setCurrentIndex(index)

    def _refresh_presets(self) -> None:
        selected = self.preset_list.currentItem().text() if self.preset_list.currentItem() \
            else ""
        self.preset_list.clear()
        for name, look in self.ctl.presets().items():
            item = QListWidgetItem(name)
            full = config.Settings(**config.preset_look(look))
            full.size = min(full.size, 34)
            item.setIcon(QIcon(render.pixmap(full, 36, QColor(BG))))
            if name in config.BUILTIN_PRESETS and name not in self.s.presets:
                item.setToolTip("Built-in preset")
            self.preset_list.addItem(item)
            if name == selected:
                self.preset_list.setCurrentItem(item)

    # -- actions ------------------------------------------------------------------------
    def _preview(self, zoom: int | None = None, background: str | None = None) -> None:
        self.preview.zoom = zoom or self.preview.zoom
        self.preview.background = background or self.preview.background
        self.preview.update()

    def _step(self) -> int:
        return int(self.step.currentText().split()[0])

    def _pick_style(self, item: QListWidgetItem) -> None:
        style = item.data(Qt.ItemDataRole.UserRole)
        if style == "image" and not self.s.image and not self._choose_image():
            self.sync([])
            return
        self.ctl.update(style=style)

    def _pick_color(self, key: str) -> None:
        color = QColorDialog.getColor(QColor(getattr(self.s, key)), self, "Crosshair colour")
        if color.isValid():
            self.ctl.update(**{key: color.name()})

    def _choose_image(self) -> bool:
        types = " ".join(f"*.{t}" for t in render.IMAGE_TYPES)
        start = str(Path(self.s.image).parent) if self.s.image else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Crosshair image", start,
                                              f"Images ({types});;All files (*)")
        if not path:
            return False
        self.ctl.update(image=path, style="image")
        return True

    def _pick_screen(self, index: int) -> None:
        data = self.screen_box.itemData(index)
        if data == "*":
            self.ctl.update(all_screens=True)
        else:
            self.ctl.update(screen=data, all_screens=False)

    def _apply_preset(self) -> None:
        item = self.preset_list.currentItem()
        if item:
            self.ctl.apply_preset(item.text())

    def _save_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Save preset", "Name for the current crosshair:")
        name = name.strip()
        if ok and name:
            self.ctl.save_preset(name)
            self.status.setText(f"Saved preset “{name}”.")

    def _delete_preset(self) -> None:
        item = self.preset_list.currentItem()
        if not item:
            return
        if item.text() not in self.s.presets:
            self.status.setText("Built-in presets can't be deleted.")
            return
        self.ctl.delete_preset(item.text())

    def _export_presets(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export presets",
                                              str(Path.home() / "void-crosshair-presets.json"),
                                              "JSON (*.json)")
        if path:
            Path(path).write_text(json.dumps({"presets": self.ctl.presets(),
                                              "current": self.s.look()}, indent=2))
            self.status.setText(f"Exported to {path}")

    def _import_presets(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import presets", str(Path.home()),
                                              "JSON (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text())
            found = {str(k): config.preset_look(v) for k, v in data.get("presets", {}).items()
                     if isinstance(v, dict)}
        except (OSError, ValueError, AttributeError) as exc:
            QMessageBox.warning(self, APP_NAME, f"Couldn't read that file:\n{exc}")
            return
        new = {k: v for k, v in found.items() if k not in config.BUILTIN_PRESETS}
        self.ctl.update(presets={**self.s.presets, **new})
        self.status.setText(f"Imported {len(new)} preset(s).")

    def _set_autostart(self, on: bool) -> None:
        try:
            desktop.set_autostart(on)
        except OSError as exc:
            self.status.setText(f"Couldn't change autostart: {exc}")

    def _configure_shortcuts(self) -> None:
        sc = self.ctl.shortcuts
        if sc is None or not sc.configure():
            self.status.setText("Your desktop doesn't offer that dialog. Change the keys in "
                                "System Settings → Shortcuts, or bind terminal commands.")

    def _shortcut_status(self, working: bool | None, message: str) -> None:
        sc = self.ctl.shortcuts
        if working is None and sc is not None and sc.bound:
            working, message = True, "Global shortcuts active (desktop portal)."
        if message:
            colour = GREEN if working else AMBER
            self.shortcut_state.setText(f"<span style='color:{colour}'>●</span> {message}")
        bound = sc.bound if sc is not None else {}
        rows = []
        for sid, desc, trigger in SHORTCUTS:
            keys = bound.get(sid) or trigger.replace("+", " + ").title()
            rows.append(f"{keys:<30} {desc}")
        self.shortcut_list.setText("\n".join(rows))

    def closeEvent(self, event) -> None:
        # The crosshair keeps running; the window only hides.
        event.ignore()
        self.hide()
