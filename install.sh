#!/usr/bin/env bash
# Installiert den Cachy Software-Kompass für den aktuellen Benutzer.
#
# Was passiert:
#   1. Fehlende Pakete werden mit pacman installiert (fragt nach dem Passwort):
#        - pyside6         → für die grafische Oberfläche
#        - pacman-contrib  → für die genaue Update-Prüfung (Befehl „checkupdates“)
#   2. Das Programm wird nach ~/.local/share/cachy-kompass kopiert.
#   3. Ein Startbefehl ~/.local/bin/cachy-kompass wird angelegt.
#   4. Ein Startmenü-Eintrag „Cachy Software-Kompass“ wird angelegt.
#
# Es wird nichts außerhalb deines Benutzerordners verändert (außer Schritt 1).

set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$HOME/.local/share/cachy-kompass"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
LAUNCHER="$BIN_DIR/cachy-kompass"
DESKTOP_FILE="$APPS_DIR/cachy-kompass.desktop"

echo "== Cachy Software-Kompass wird installiert =="

if ! command -v pacman >/dev/null 2>&1; then
    echo "Hinweis: pacman wurde nicht gefunden. Das Programm ist für CachyOS/Arch gedacht."
fi

missing=()
python3 -c "import PySide6" 2>/dev/null || missing+=(pyside6)
command -v checkupdates >/dev/null 2>&1 || missing+=(pacman-contrib)

if ((${#missing[@]})) && command -v pacman >/dev/null 2>&1; then
    echo
    echo "Folgende Pakete werden noch benötigt: ${missing[*]}"
    echo "Sie werden jetzt mit pacman installiert (dazu wird dein Passwort abgefragt)."
    sudo pacman -S --needed "${missing[@]}"
fi

if [[ -d "$TARGET" ]]; then
    echo "→ Eine ältere Version ist bereits installiert – sie wird ersetzt."
fi
echo "→ Kopiere Programm nach $TARGET"
rm -rf "$TARGET"
mkdir -p "$TARGET"
cp -r "$SRC_DIR/cachy_kompass" "$TARGET/"
find "$TARGET" -name "__pycache__" -type d -prune -exec rm -rf {} +

echo "→ Lege Startbefehl $LAUNCHER an"
mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/bin/sh
# Startet den Cachy Software-Kompass (angelegt von install.sh)
PYTHONPATH="$TARGET\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m cachy_kompass "\$@"
EOF
chmod 755 "$LAUNCHER"

echo "→ Lege Startmenü-Eintrag an"
mkdir -p "$APPS_DIR"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Version=1.5
Name=Cachy Software-Kompass
GenericName=Programm-Übersicht
Comment=Zeigt installierte Programme, ihre Herkunft und ihren Startmenü-Status
Exec=$LAUNCHER
Icon=system-software-install
Terminal=false
Categories=System;Settings;
Keywords=Programme;Pakete;Startmenü;Software;AUR;Flatpak;
EOF
chmod 644 "$DESKTOP_FILE"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS_DIR" || true
if command -v kbuildsycoca6 >/dev/null 2>&1; then kbuildsycoca6 >/dev/null 2>&1 || true; fi

echo
echo "Fertig! Du findest den „Cachy Software-Kompass“ jetzt im Startmenü."
echo "Alternativ im Terminal starten mit:  cachy-kompass"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "(Hinweis: $BIN_DIR ist nicht in deinem PATH – im Terminal ggf. mit vollem Pfad starten: $LAUNCHER)" ;;
esac
