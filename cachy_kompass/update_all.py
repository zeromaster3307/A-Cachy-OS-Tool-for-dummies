"""„Alles aktualisieren“: Welche Update-Befehle passen zu diesem System?

Wie überall im Software-Kompass gilt: Die Befehle laufen sichtbar in einem
Terminalfenster. pacman/paru fragen dort vor dem Installieren nach, und du gibst
dein Passwort selbst ein.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cachy_kompass import util
from cachy_kompass.i18n import _
from cachy_kompass.models import Program, Source


@dataclass
class UpdateStep:
    key: str
    label: str
    explanation: str
    command: list[str]
    #: Standardmäßig angehakt?
    default: bool = True


def plan(programs: list[Program], which: Callable[[str], str | None] = util.which) -> list[UpdateStep]:
    """Die Update-Schritte, die auf diesem System sinnvoll sind."""
    sources = {p.source for p in programs}
    steps: list[UpdateStep] = []

    if which("paru"):
        steps.append(UpdateStep(
            "system", _("System + AUR (paru)"),
            _("Aktualisiert alle Pakete aus den Repos und dem AUR – das normale CachyOS-Systemupdate."),
            ["paru", "-Syu"],
        ))
    elif which("yay"):
        steps.append(UpdateStep(
            "system", _("System + AUR (yay)"),
            _("Aktualisiert alle Pakete aus den Repos und dem AUR – das normale Systemupdate."),
            ["yay", "-Syu"],
        ))
    elif which("pacman"):
        note = " " + _("AUR-Pakete werden dabei nicht aktualisiert (dafür paru installieren).") if Source.AUR in sources else ""
        steps.append(UpdateStep(
            "system", _("System (pacman)"),
            _("Aktualisiert alle Pakete aus den Repos – das normale Systemupdate.") + note,
            ["sudo", "pacman", "-Syu"],
        ))

    if which("flatpak") and Source.FLATPAK in sources:
        steps.append(UpdateStep(
            "flatpak", _("Flatpak-Apps"),
            _("Aktualisiert alle Flatpak-Apps und ihre Laufzeiten."),
            ["flatpak", "update"],
        ))
    if which("pipx") and Source.PIPX in sources:
        steps.append(UpdateStep(
            "pipx", _("pipx-Programme (Python)"),
            _("Aktualisiert alle mit pipx installierten Python-Programme in deinem Benutzerordner."),
            ["pipx", "upgrade-all"],
        ))
    if which("uv") and Source.UV in sources:
        steps.append(UpdateStep(
            "uv", _("uv-Programme (Python)"),
            _("Aktualisiert alle mit „uv tool“ installierten Python-Programme."),
            ["uv", "tool", "upgrade", "--all"],
        ))
    if which("cargo-install-update") and Source.CARGO in sources:
        steps.append(UpdateStep(
            "cargo", _("cargo-Programme (Rust)"),
            _("Baut alle mit cargo installierten Programme in neuer Version (kann lange dauern)."),
            ["cargo", "install-update", "-a"],
            default=False,
        ))
    brew = which("brew")
    if brew and Source.BREW in sources:
        steps.append(UpdateStep(
            "brew", "Homebrew",
            _("Aktualisiert alle mit Homebrew installierten Programme."),
            [brew, "upgrade"],
            default=False,
        ))
    return steps


def not_covered(programs: list[Program], steps: list[UpdateStep]) -> list[str]:
    """Hinweise zu Programmen, die „Alles aktualisieren“ nicht erfasst."""
    keys = {s.key for s in steps}
    sources = {p.source for p in programs if p.explicit}
    notes = []
    if Source.SNAP in sources:
        notes.append(_("Snap-Pakete aktualisieren sich selbst im Hintergrund."))
    if Source.NPM in sources:
        notes.append(_("npm-Programme: „npm update -g“ (je nach Einrichtung mit sudo)."))
    if Source.CARGO in sources and "cargo" not in keys:
        notes.append(_("cargo-Programme: einzeln mit „cargo install <name>“ neu bauen."))
    if Source.APPIMAGE in sources:
        notes.append(_("AppImages: neue Version selbst herunterladen (oder Gear Lever nutzen)."))
    if Source.MANUAL in sources:
        notes.append(_("Von Hand installierte Programme: beim Hersteller nach Updates schauen."))
    return notes
