"""Befehle sichtbar in einem Terminalfenster ausführen.

Der Software-Kompass führt nie selbst etwas mit Administratorrechten aus.
Stattdessen öffnet er ein Terminal (z. B. Konsole), zeigt dort den Befehl an,
und du gibst dein Passwort selbst ein. So siehst du genau, was passiert.
"""

from __future__ import annotations

import shlex
import subprocess

from cachy_kompass import util

# Terminal → Argumente, nach denen der auszuführende Befehl folgt.
# Reihenfolge = Vorliebe (KDE zuerst, weil Standard unter CachyOS).
TERMINALS: list[tuple[str, list[str]]] = [
    ("konsole", ["-e"]),
    ("kgx", ["--"]),
    ("gnome-terminal", ["--"]),
    ("ptyxis", ["--"]),
    ("kitty", []),
    ("alacritty", ["-e"]),
    ("foot", []),
    ("wezterm", ["start", "--"]),
    ("ghostty", ["-e"]),
    ("xfce4-terminal", ["-x"]),
    ("tilix", ["-e"]),
    ("xterm", ["-e"]),
]


def find_terminal() -> tuple[str, list[str]] | None:
    for name, args in TERMINALS:
        path = util.which(name)
        if path:
            return path, args
    return None


def build_script(command: list[str]) -> str:
    """Kleines Shell-Skript: Befehl anzeigen, ausführen, Ergebnis melden, auf Enter warten."""
    cmd = shlex.join(command)
    return (
        'echo "Cachy Software-Kompass – folgender Befehl wird ausgeführt:"; echo; '
        f"echo {shlex.quote('    ' + cmd)}; echo; "
        f"{cmd}; status=$?; echo; "
        'if [ "$status" -eq 0 ]; then echo "✔ Fertig. Klicke im Software-Kompass auf „Neu einlesen“."; '
        'else echo "✘ Nicht erfolgreich (Code $status). Es wurde nichts verändert, falls du abgebrochen hast."; fi; '
        'echo; read -r -p "Enter drücken, um dieses Fenster zu schließen …" _'
    )


def terminal_argv(command: list[str], terminal: tuple[str, list[str]]) -> list[str]:
    path, args = terminal
    return [path, *args, "bash", "-c", build_script(command)]


def run_in_terminal(command: list[str]) -> bool:
    """Öffnet ein Terminal mit dem Befehl. ``False``, wenn kein Terminal gefunden wurde."""
    terminal = find_terminal()
    if terminal is None:
        return False
    subprocess.Popen(
        terminal_argv(command, terminal),
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True
