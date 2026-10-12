"""Settings and presets: one JSON file in ~/.config/the-void-crosshair/."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from void_crosshair import APP_SLUG

STYLES = ("cross", "cross_dot", "t", "x", "dot", "circle", "circle_dot", "circle_cross",
          "chevron", "square", "triangle", "image")
STYLE_NAMES = {"cross": "Cross", "cross_dot": "Cross dot", "t": "T-shape", "x": "X",
               "dot": "Dot", "circle": "Circle", "circle_dot": "Circle dot",
               "circle_cross": "Circle cross", "chevron": "Chevron", "square": "Square",
               "triangle": "Triangle", "image": "Image"}

# The fields that make up a crosshair's look (what a preset stores).
LOOK = ("style", "color", "opacity", "size", "thickness", "gap", "dot", "outline",
        "outline_color", "outline_width", "rotation", "image", "tint_image")

# (min, max) for every number; values outside are clamped, never rejected.
RANGES = {"opacity": (0.05, 1.0), "size": (4, 256), "thickness": (1, 32), "gap": (0, 64),
          "dot": (0, 32), "outline_width": (0, 8), "rotation": (-180, 180),
          "offset_x": (-4000, 4000), "offset_y": (-4000, 4000)}

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass
class Settings:
    style: str = "cross_dot"
    color: str = "#00FF66"
    opacity: float = 1.0
    size: int = 24
    thickness: int = 2
    gap: int = 4
    dot: int = 2
    outline: bool = True
    outline_color: str = "#000000"
    outline_width: int = 1
    rotation: int = 0
    image: str = ""
    tint_image: bool = False
    offset_x: int = 0
    offset_y: int = 0
    screen: str = ""            # screen name; empty = primary
    all_screens: bool = False   # mirror the crosshair on every display
    visible: bool = True
    open_settings_on_start: bool = True
    presets: dict[str, dict] = field(default_factory=dict)

    def look(self) -> dict:
        return {k: getattr(self, k) for k in LOOK}

    def update(self, **values) -> list[str]:
        """Set known fields (cleaned up); return the names that actually changed."""
        changed = []
        names = {f.name for f in fields(self)}
        for key, value in values.items():
            if key not in names:
                raise KeyError(f"unknown setting: {key}")
            value = clean(key, value, getattr(self, key))
            if value != getattr(self, key):
                setattr(self, key, value)
                changed.append(key)
        return changed


def clean(key: str, value, current):
    """Coerce a value to the field's type and range; fall back to the current value."""
    if key in RANGES:
        lo, hi = RANGES[key]
        try:
            num = float(value)
        except (TypeError, ValueError):
            return current
        num = min(max(num, lo), hi)
        return round(num, 2) if isinstance(current, float) else int(round(num))
    if isinstance(current, bool):
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    if key in ("color", "outline_color"):
        value = str(value).strip()
        if re.fullmatch(r"[0-9A-Fa-f]{6}", value):
            value = "#" + value
        return value.upper() if HEX.match(value) else current
    if key == "style":
        return value if value in STYLES else current
    if key == "presets":
        return value if isinstance(value, dict) else current
    return str(value)


# Built-in presets; user presets (same shape) are saved alongside the settings.
BUILTIN_PRESETS: dict[str, dict] = {
    "THE VOID": dict(style="cross_dot", color="#D90429", size=26, thickness=2, gap=5, dot=2,
                     outline=True, outline_color="#000000", outline_width=1),
    "Classic green": dict(style="cross", color="#00FF66", size=22, thickness=2, gap=4,
                          outline=True, outline_width=1),
    "Tiny dot": dict(style="dot", color="#00FFFF", dot=2, outline=True, outline_width=1),
    "Tactical circle": dict(style="circle_dot", color="#FFFFFF", size=30, thickness=1, dot=1,
                            outline=True, outline_width=1),
    "Sniper": dict(style="circle_cross", color="#FF2D55", size=64, thickness=1, gap=10,
                   outline=False),
    "Chevron": dict(style="chevron", color="#FFD400", size=18, thickness=2, outline=True,
                    outline_width=1),
    "Big X": dict(style="x", color="#FF00FF", size=28, thickness=3, gap=6, outline=True,
                  outline_width=1),
}


def preset_look(values: dict) -> dict:
    """A full look: defaults filled in, unknown keys dropped."""
    base = Settings().look()
    base.update({k: v for k, v in values.items() if k in LOOK})
    return base


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / APP_SLUG


def load(path: Path | None = None) -> Settings:
    path = path or config_dir() / "settings.json"
    s = Settings()
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return s
    if isinstance(data, dict):
        known = {f.name for f in fields(s)}
        s.update(**{k: v for k, v in data.items() if k in known})
    return s


def save(s: Settings, path: Path | None = None) -> None:
    path = path or config_dir() / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(s), indent=2))
    tmp.replace(path)
