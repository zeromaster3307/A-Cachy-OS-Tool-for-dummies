"""Programmliste sichern: ein Skript, das nach einer Neuinstallation alles wieder einspielt.

Das Ergebnis ist ein gut lesbares bash-Skript. Es ist gleichzeitig eine Notiz
„Was hatte ich eigentlich alles installiert?“. Ausgeführt wird es nur, wenn du
es selbst startest – und auch dann fragen pacman, paru und Co. vor jeder
Installation noch einmal nach.
"""

from __future__ import annotations

import shlex
from datetime import datetime

from cachy_kompass import APP_NAME, __version__
from cachy_kompass.models import Program, Source


def _names(programs: list[Program], source: Source) -> list[str]:
    return sorted({p.name for p in programs if p.source is source and p.explicit})


def _wrap(prefix: list[str], names: list[str], per_line: int = 6) -> str:
    """Lange Paketlisten auf mehrere Zeilen verteilen (mit „\\“ am Zeilenende)."""
    lines = [" ".join(shlex.quote(n) for n in names[i : i + per_line]) for i in range(0, len(names), per_line)]
    return shlex.join(prefix) + " \\\n    " + " \\\n    ".join(lines)


def build_script(programs: list[Program], now: datetime | None = None, hostname: str = "") -> str:
    now = now or datetime.now()
    explicit = [p for p in programs if p.explicit]
    out = [
        "#!/usr/bin/env bash",
        f"# Programmliste, gesichert mit dem {APP_NAME} {__version__}",
        f"# am {now:%d.%m.%Y um %H:%M}" + (f" auf „{hostname}“" if hostname else ""),
        "#",
        "# So stellst du die Programme nach einer Neuinstallation wieder her:",
        "#   1. Diese Datei z. B. auf einen USB-Stick oder in die Cloud kopieren.",
        "#   2. Auf dem neuen System im Terminal ausführen:  bash <dateiname>",
        "#      (CachyOS nutzt die fish-Shell – deshalb ausdrücklich „bash“ davor schreiben.)",
        "#   3. Jeder Schritt fragt vor dem Installieren nach. Mit „n“ überspringst du ihn.",
        "#",
        "# Du kannst die Datei vorher mit einem Texteditor anpassen: Zeilen, die mit „#“",
        "# beginnen, werden nicht ausgeführt. Einstellungen und Dateien der Programme sind",
        "# NICHT enthalten – die liegen in deinem Benutzerordner (z. B. ~/.config).",
        "",
        "set -u",
        "",
        "ask() {",
        '    read -r -p "$1 [J/n] " answer',
        '    [[ -z "$answer" || "$answer" =~ ^[JjYy] ]]',
        "}",
        "",
    ]

    repo = _names(explicit, Source.REPO)
    if repo:
        out += [
            f"# --- Offizielle Repos (CachyOS/Arch): {len(repo)} Pakete ---",
            "# „--needed“ überspringt, was schon installiert ist. Meldet pacman „target not",
            "# found“, gibt es ein Paket nicht mehr: dann den Namen unten löschen und neu starten.",
            f'if ask "{len(repo)} Pakete aus den offiziellen Repos installieren?"; then',
            "    " + _wrap(["sudo", "pacman", "-S", "--needed"], repo).replace("\n", "\n    "),
            "fi",
            "",
        ]

    aur = _names(explicit, Source.AUR)
    if aur:
        out += [
            f"# --- AUR: {len(aur)} Pakete ---",
            "# Braucht den AUR-Helfer paru (unter CachyOS vorinstalliert). AUR-Pakete sind",
            "# nicht offiziell geprüft – entferne vorher, was du nicht mehr brauchst.",
            "# Pakete, die es im AUR nicht mehr gibt, meldet paru als Fehler.",
            f'if command -v paru >/dev/null && ask "{len(aur)} Pakete aus dem AUR installieren?"; then',
            "    " + _wrap(["paru", "-S", "--needed"], aur).replace("\n", "\n    "),
            "fi",
            "",
        ]

    flatpaks = [p for p in explicit if p.source is Source.FLATPAK]
    if flatpaks:
        out += [f"# --- Flatpak: {len(flatpaks)} Apps ---"]
        out += ['if command -v flatpak >/dev/null && ask "Flatpak-Apps installieren?"; then']
        for scope in ("system", "user"):
            ids = sorted(p.name for p in flatpaks if (p.installation or "system") == scope)
            if not ids:
                continue
            flag = "--user" if scope == "user" else "--system"
            if scope == "user":
                out.append("    flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo")
            out.append("    " + _wrap(["flatpak", "install", flag, "flathub"], ids).replace("\n", "\n    "))
        out += ["fi", ""]

    simple: list[tuple[Source, str, list[str]]] = [
        (Source.SNAP, "Snap", ["sudo", "snap", "install"]),
        (Source.PIPX, "pipx (Python)", ["pipx", "install"]),
        (Source.UV, "uv tool (Python)", ["uv", "tool", "install"]),
        (Source.CARGO, "cargo (Rust)", ["cargo", "install"]),
        (Source.NPM, "npm (Node.js)", ["npm", "install", "-g"]),
        (Source.BREW, "Homebrew", ["brew", "install"]),
    ]
    for source, label, cmd in simple:
        progs = [p for p in explicit if p.source is source]
        if source is Source.CARGO:
            # Aus einem Git-Repo gebaute Programme lassen sich nicht per Name installieren
            progs = [p for p in progs if not p.install_path]
        names = sorted({p.name for p in progs})
        if not names:
            continue
        tool = cmd[1] if cmd[0] == "sudo" else cmd[0]
        out += [
            f"# --- {label}: {len(names)} Programme ---",
            f"# Braucht „{tool}“ – falls es fehlt, zuerst über den {APP_NAME} (Reiter „Paketverwaltungen“) installieren.",
            f'if command -v {tool} >/dev/null && ask "{label}: {len(names)} Programme installieren?"; then',
        ]
        out += [f"    {shlex.join([*cmd, n])}" for n in names]
        out += ["fi", ""]

    manual = [p for p in explicit if p.source in (Source.APPIMAGE, Source.MANUAL) and not p.uninstall_override]
    git_cargo = [p for p in explicit if p.source is Source.CARGO and p.install_path]
    if manual or git_cargo:
        out += [
            "# --- Nicht automatisch wiederherstellbar ---",
            "# Diese Programme wurden von Hand heruntergeladen oder gebaut. Lade sie bei",
            "# Bedarf neu von der Webseite des Herstellers:",
        ]
        out += [f"#   • {p.display_name}  ({p.info.label}: {p.install_path})" for p in manual + git_cargo]
        out.append("")

    out += ['echo "Fertig."', ""]
    return "\n".join(out)


def default_filename(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"programme-{now:%Y-%m-%d}.sh"
