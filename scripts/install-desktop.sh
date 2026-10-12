#!/usr/bin/env bash
# Add THE VOID CROSSHAIR to the application menu for this user (no root needed).
#   bash scripts/install-desktop.sh                       from this source folder
#   bash scripts/install-desktop.sh --appimage FILE       install a built AppImage
#   bash scripts/install-desktop.sh --remove              uninstall
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ID="com.thevoid.Crosshair"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor"
AUTOSTART="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$APP_ID.desktop"

if [ "${1:-}" = "--remove" ]; then
    "$BIN/void-crosshair" quit >/dev/null 2>&1 || true
    rm -f "$BIN/the-void-crosshair" "$BIN/void-crosshair" "$APPS/$APP_ID.desktop" "$AUTOSTART" \
          "$HOME/Applications"/THE-VOID-CROSSHAIR-*.AppImage
    rm -f "$ICONS"/*/apps/"$APP_ID".*
    command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true
    echo "Removed. (Settings and presets: ~/.config/the-void-crosshair)"
    exit 0
fi

mkdir -p "$BIN" "$APPS" "$ICONS"
"$BIN/void-crosshair" quit >/dev/null 2>&1 || true     # replace a running older copy
rm -f "$BIN/the-void-crosshair" "$BIN/void-crosshair"
if [ "${1:-}" = "--appimage" ]; then
    SRC="$(readlink -f "${2:?give the AppImage file}")"
    mkdir -p "$HOME/Applications"
    rm -f "$HOME/Applications"/THE-VOID-CROSSHAIR-*.AppImage
    TARGET="$HOME/Applications/$(basename "$SRC")"
    cp "$SRC" "$TARGET"
    chmod +x "$TARGET"
    ln -s "$TARGET" "$BIN/the-void-crosshair"
    ln -s "$TARGET" "$BIN/void-crosshair"
else
    [ -x "$ROOT/.venv/bin/python" ] || bash "$ROOT/scripts/setup.sh"
    # Launchers point at this source folder's environment.
    printf '#!/bin/sh\nexec "%s/.venv/bin/python" -m void_crosshair "$@"\n' "$ROOT" \
        > "$BIN/the-void-crosshair"
    ln -s "$BIN/the-void-crosshair" "$BIN/void-crosshair"
    chmod +x "$BIN/the-void-crosshair"
fi
sed "s|^Exec=the-void-crosshair|Exec=$BIN/the-void-crosshair|" "$ROOT/data/$APP_ID.desktop" \
    > "$APPS/$APP_ID.desktop"
cp -r "$ROOT/data/icons/hicolor/." "$ICONS/"
# An enabled autostart entry keeps pointing at the right launcher.
if [ -f "$AUTOSTART" ]; then
    sed -i "s|^Exec=.*|Exec=$BIN/the-void-crosshair --background|" "$AUTOSTART"
fi
command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true
echo "Installed: application menu → THE VOID CROSSHAIR;  terminal: void-crosshair --help"
