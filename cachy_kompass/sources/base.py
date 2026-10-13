"""Gemeinsame Basis für alle Installationsquellen."""

from __future__ import annotations

from dataclasses import dataclass, field

from cachy_kompass.i18n import _
from cachy_kompass.models import Program, Source, UpdateResult, UpdateStatus


@dataclass
class ScanContext:
    """Was bisher gefunden wurde – damit spätere Quellen Doppelungen vermeiden."""

    programs: list[Program] = field(default_factory=list)
    #: Dateien und Ordner in /opt und /usr/local, die laut pacman zu einem Paket
    #: gehören (ohne „/“ am Ende). Damit erkennt die Suche nach manuell
    #: installierten Programmen, was doch von pacman stammt.
    pacman_paths: set[str] = field(default_factory=set)
    #: Namen von Hilfsprogrammen, die zu Paketen gehören, aber nicht im Suchpfad
    #: liegen (z. B. „kiod6“ in /usr/lib/kf6). Startmenü-Einträge, die sie ohne
    #: Pfad aufrufen, sind deshalb nicht kaputt.
    helper_names: set[str] = field(default_factory=set)

    def known_executables(self) -> set[str]:
        return {exe for p in self.programs for exe in p.executables}


class PackageSource:
    """Eine Installationsquelle (pacman, Flatpak, pipx, …).

    Unterklassen implementieren:
      * ``is_available`` – ist das Werkzeug überhaupt installiert?
      * ``scan``          – welche Programme wurden damit installiert?
      * ``check_updates`` – gibt es neuere Versionen? (optional)
    """

    #: Kurzer Name für Fortschrittsmeldungen
    title: str = ""
    #: Welche ``Source``-Werte diese Quelle liefert und prüfen kann
    handles: tuple[Source, ...] = ()

    def is_available(self) -> bool:
        raise NotImplementedError

    def scan(self, ctx: ScanContext) -> list[Program]:
        raise NotImplementedError

    def check_updates(self, programs: list[Program]) -> dict[str, UpdateResult]:
        """Liefert pro ``Program.key`` ein Ergebnis. Standard: nicht prüfbar."""
        note = _("Für diese Art von Programm gibt es keine zentrale Versionsliste.")
        return {p.key: UpdateResult(UpdateStatus.NOT_CHECKABLE, note=note) for p in programs}


def compare_result(installed: str, latest: str | None, note: str = "") -> UpdateResult:
    """Einfacher Vergleich: gleiche Version = aktuell, sonst Update verfügbar."""
    if not latest:
        return UpdateResult(UpdateStatus.UNKNOWN, note=note or _("Keine Versionsinformation gefunden."))
    if installed.lstrip("v") == latest.lstrip("v"):
        return UpdateResult(UpdateStatus.CURRENT, latest, note)
    return UpdateResult(UpdateStatus.OUTDATED, latest, note)
