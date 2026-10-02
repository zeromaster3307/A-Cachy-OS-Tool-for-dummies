#!/usr/bin/env bash
# Entfernt den Cachy Software-Kompass wieder.
#
# Die Pakete pyside6 und pacman-contrib bleiben installiert, weil andere
# Programme sie evtl. auch nutzen. Startmenü-Einträge, die du mit dem
# Software-Kompass angelegt hast, bleiben ebenfalls erhalten – sie werden nur
# gelöscht, wenn du beim Nachfragen „j“ eingibst.

set -euo pipefail

APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

rm -rf "$HOME/.local/share/cachy-kompass"
rm -f "$HOME/.local/bin/cachy-kompass"
rm -f "$APPS_DIR/cachy-kompass.desktop"
echo "Cachy Software-Kompass wurde entfernt."

shopt -s nullglob
own=("$APPS_DIR"/cachy-kompass-*.desktop)
if ((${#own[@]})); then
    echo
    echo "Es gibt noch ${#own[@]} Startmenü-Einträge, die du mit dem Software-Kompass angelegt hast:"
    printf '  %s\n' "${own[@]}"
    read -r -p "Sollen diese auch gelöscht werden? [j/N] " answer
    if [[ "$answer" =~ ^[jJyY]$ ]]; then
        rm -f "${own[@]}"
        echo "Einträge gelöscht."
    fi
fi

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS_DIR" || true
if command -v kbuildsycoca6 >/dev/null 2>&1; then kbuildsycoca6 >/dev/null 2>&1 || true; fi
