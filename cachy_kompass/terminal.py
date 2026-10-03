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


Command = list[str]


def _as_commands(command: Command | list[Command]) -> list[Command]:
    """Ein einzelner Befehl oder eine Liste von Befehlen → immer eine Liste von Befehlen."""
    if command and isinstance(command[0], list):
        return command  # type: ignore[return-value]
    return [command]  # type: ignore[list-item]


def describe(command: Command | list[Command]) -> str:
    """Befehl(e) so, wie man sie selbst ins Terminal tippen würde (für Anzeige und Zwischenablage)."""
    return " && ".join(shlex.join(c) for c in _as_commands(command))


def build_script(command: Command | list[Command]) -> str:
    """Kleines Shell-Skript: Befehl(e) anzeigen, nacheinander ausführen, Ergebnis melden, auf Enter warten.

    Mehrere Befehle laufen mit „&&“: schlägt einer fehl, werden die folgenden nicht ausgeführt.
    """
    commands = _as_commands(command)
    shown = "; ".join(f"echo {shlex.quote('    ' + shlex.join(c))}" for c in commands)
    word = "folgender Befehl wird" if len(commands) == 1 else "folgende Befehle werden"
    return (
        f'echo "Cachy Software-Kompass – {word} ausgeführt:"; echo; '
        f"{shown}; echo; "
        f"{describe(commands)}; status=$?; echo; "
        'if [ "$status" -eq 0 ]; then echo "✔ Fertig. Klicke im Software-Kompass auf „Neu einlesen“."; '
        'else echo "✘ Nicht erfolgreich (Code $status). Es wurde nichts verändert, falls du abgebrochen hast."; fi; '
        'echo; read -r -p "Enter drücken, um dieses Fenster zu schließen …" _'
    )


def terminal_argv(command: Command | list[Command], terminal: tuple[str, list[str]]) -> list[str]:
    path, args = terminal
    return [path, *args, "bash", "-c", build_script(command)]


def run_in_terminal(command: Command | list[Command]) -> bool:
    """Öffnet ein Terminal mit dem Befehl bzw. den Befehlen. ``False``, wenn kein Terminal gefunden wurde."""
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
