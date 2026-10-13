"""Programmliste sichern: ein Skript, das nach einer Neuinstallation alles wieder einspielt.

Das Ergebnis ist ein gut lesbares bash-Skript. Es ist gleichzeitig eine Notiz
„Was hatte ich eigentlich alles installiert?“. Ausgeführt wird es nur, wenn du
es selbst startest – und auch dann fragen pacman, paru und Co. vor jeder
Installation noch einmal nach.
"""

from __future__ import annotations

import shlex
from datetime import datetime

from cachy_kompass import APP_NAME, __version__, i18n
from cachy_kompass.i18n import _, ngettext
from cachy_kompass.models import Program, Source


def _names(programs: list[Program], source: Source) -> list[str]:
    return sorted({p.name for p in programs if p.source is source and p.explicit})


def _wrap(prefix: list[str], names: list[str], per_line: int = 6) -> str:
    """Lange Paketlisten auf mehrere Zeilen verteilen (mit „\\“ am Zeilenende)."""
    lines = [" ".join(shlex.quote(n) for n in names[i : i + per_line]) for i in range(0, len(names), per_line)]
    return shlex.join(prefix) + " \\\n    " + " \\\n    ".join(lines)


def _comment(text: str) -> list[str]:
    """Mehrzeiliger Text → Kommentarzeilen fürs Skript."""
    return [f"# {line}".rstrip() for line in text.splitlines()]


def _ask(question: str) -> str:
    """Frage für ``ask``: steht im Skript in doppelten Anführungszeichen – $, `, \\ und " entfernen."""
    return "".join(c for c in question if c not in '$`\\"')


def build_script(programs: list[Program], now: datetime | None = None, hostname: str = "") -> str:
    now = now or datetime.now()
    explicit = [p for p in programs if p.explicit]
    when = _("am {date} um {time}").format(date=i18n.date(now), time=f"{now:%H:%M}")
    if hostname:
        when += " " + _("auf „{host}“").format(host=hostname)
    out = [
        "#!/usr/bin/env bash",
        "# " + _("Programmliste, gesichert mit dem {app} {version}").format(app=APP_NAME, version=__version__),
        "# " + when,
        "#",
        *_comment(_(
            "So stellst du die Programme nach einer Neuinstallation wieder her:\n"
            "  1. Diese Datei z. B. auf einen USB-Stick oder in die Cloud kopieren.\n"
            "  2. Auf dem neuen System im Terminal ausführen:  bash <dateiname>\n"
            "     (CachyOS nutzt die fish-Shell – deshalb ausdrücklich „bash“ davor schreiben.)\n"
            "  3. Jeder Schritt fragt vor dem Installieren nach. Mit „n“ überspringst du ihn.\n"
            "\n"
            "Du kannst die Datei vorher mit einem Texteditor anpassen: Zeilen, die mit „#“\n"
            "beginnen, werden nicht ausgeführt. Einstellungen und Dateien der Programme sind\n"
            "NICHT enthalten – die liegen in deinem Benutzerordner (z. B. ~/.config)."
        )),
        "",
        "set -u",
        "",
        "ask() {",
        f'    read -r -p "$1 {_ask(_("[J/n]"))} " answer',
        '    [[ -z "$answer" || "$answer" =~ ^[JjYy] ]]',
        "}",
        "",
    ]

    repo = _names(explicit, Source.REPO)
    if repo:
        n = len(repo)
        question = ngettext("{n} Paket aus den offiziellen Repos installieren?", "{n} Pakete aus den offiziellen Repos installieren?", n)
        out += [
            "# --- " + ngettext("Offizielle Repos (CachyOS/Arch): {n} Paket", "Offizielle Repos (CachyOS/Arch): {n} Pakete", n).format(n=n) + " ---",
            *_comment(_(
                "„--needed“ überspringt, was schon installiert ist. Meldet pacman „target not\n"
                "found“, gibt es ein Paket nicht mehr: dann den Namen unten löschen und neu starten."
            )),
            f'if ask "{_ask(question.format(n=n))}"; then',
            "    " + _wrap(["sudo", "pacman", "-S", "--needed"], repo).replace("\n", "\n    "),
            "fi",
            "",
        ]

    aur = _names(explicit, Source.AUR)
    if aur:
        n = len(aur)
        question = ngettext("{n} Paket aus dem AUR installieren?", "{n} Pakete aus dem AUR installieren?", n)
        out += [
            "# --- " + ngettext("AUR: {n} Paket", "AUR: {n} Pakete", n).format(n=n) + " ---",
            *_comment(_(
                "Braucht den AUR-Helfer paru (unter CachyOS vorinstalliert). AUR-Pakete sind\n"
                "nicht offiziell geprüft – entferne vorher, was du nicht mehr brauchst.\n"
                "Pakete, die es im AUR nicht mehr gibt, meldet paru als Fehler."
            )),
            f'if command -v paru >/dev/null && ask "{_ask(question.format(n=n))}"; then',
            "    " + _wrap(["paru", "-S", "--needed"], aur).replace("\n", "\n    "),
            "fi",
            "",
        ]

    flatpaks = [p for p in explicit if p.source is Source.FLATPAK]
    if flatpaks:
        n = len(flatpaks)
        out += ["# --- " + ngettext("Flatpak: {n} App", "Flatpak: {n} Apps", n).format(n=n) + " ---"]
        out += [f'if command -v flatpak >/dev/null && ask "{_ask(_("Flatpak-Apps installieren?"))}"; then']
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
        count = len(names)
        question = ngettext("{label}: {n} Programm installieren?", "{label}: {n} Programme installieren?", count)
        out += [
            "# --- " + ngettext("{label}: {n} Programm", "{label}: {n} Programme", count).format(label=label, n=count) + " ---",
            "# " + _("Braucht „{tool}“ – falls es fehlt, zuerst über den {app} (Reiter „Paketverwaltungen“) installieren.").format(
                tool=tool, app=APP_NAME
            ),
            f'if command -v {tool} >/dev/null && ask "{_ask(question.format(label=label, n=count))}"; then',
        ]
        out += [f"    {shlex.join([*cmd, n])}" for n in names]
        out += ["fi", ""]

    manual = [p for p in explicit if p.source in (Source.APPIMAGE, Source.MANUAL) and not p.uninstall_override]
    git_cargo = [p for p in explicit if p.source is Source.CARGO and p.install_path]
    if manual or git_cargo:
        out += [
            "# --- " + _("Nicht automatisch wiederherstellbar") + " ---",
            *_comment(_(
                "Diese Programme wurden von Hand heruntergeladen oder gebaut. Lade sie bei\n"
                "Bedarf neu von der Webseite des Herstellers:"
            )),
        ]
        out += [f"#   • {p.display_name}  ({p.info.label}: {p.install_path})" for p in manual + git_cargo]
        out.append("")

    out += [f'echo "{_ask(_("Fertig."))}"', ""]
    return "\n".join(out)


def default_filename(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return _("programme-{date}.sh").format(date=f"{now:%Y-%m-%d}")
