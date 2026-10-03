"""Führt alles zusammen: Quellen abfragen, Startmenü zuordnen, Updates prüfen."""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from cachy_kompass import desktop, duplicates, history, installers, sizes
from cachy_kompass.models import DesktopEntry, Program, Source, UpdateResult, UpdateStatus
from cachy_kompass.sources import PackageSource, ScanContext, all_sources

log = logging.getLogger(__name__)

Progress = Callable[[str], None]


@dataclass
class ScanResult:
    programs: list[Program] = field(default_factory=list)
    entries: list[DesktopEntry] = field(default_factory=list)
    unmatched_entries: list[DesktopEntry] = field(default_factory=list)
    installers: list[installers.InstallerStatus] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    #: siehe ``ScanContext.helper_names``
    helper_names: set[str] = field(default_factory=set)
    #: Programme, die doppelt (aus verschiedenen Quellen) installiert sind
    duplicate_groups: list[list[Program]] = field(default_factory=list)
    #: Ist ein Neustart fällig (z. B. nach einem Kernel-Update)?
    reboot: history.RebootInfo = field(default_factory=history.RebootInfo)

    def owner_of(self, entry: DesktopEntry) -> Program | None:
        for p in self.programs:
            if entry in p.desktop_entries:
                return p
        return None


def _noop(_: str) -> None:
    pass


def scan(progress: Progress = _noop, sources: list[PackageSource] | None = None) -> ScanResult:
    result = ScanResult()
    ctx = ScanContext()
    for src in sources if sources is not None else all_sources():
        try:
            if not src.is_available():
                continue
            progress(f"Lese {src.title} …")
            found = src.scan(ctx)
        except Exception as exc:  # eine kaputte Quelle soll nicht alles abbrechen
            log.exception("Fehler beim Lesen von %s", src.title)
            result.warnings.append(f"{src.title}: {exc}")
            continue
        ctx.programs.extend(found)

    progress("Lese Startmenü-Einträge …")
    result.programs = ctx.programs
    result.helper_names = ctx.helper_names
    result.entries = desktop.load_entries()
    result.unmatched_entries = desktop.match_entries(result.programs, result.entries)

    progress("Lese Installationsdaten …")
    events = history.read_log()
    history.fill_install_dates(result.programs, events)
    result.reboot = history.check_reboot(events, history.boot_time())

    progress("Berechne Größen …")
    sizes.fill_sizes(result.programs)
    result.duplicate_groups = duplicates.find_duplicates(result.programs)

    progress("Suche Paketverwaltungen …")
    result.installers = installers.detect(result.programs)
    result.programs.sort(key=lambda p: p.display_name.lower())
    progress(f"{sum(p.explicit for p in result.programs)} Programme gefunden.")
    return result


def check_updates(
    programs: list[Program],
    progress: Progress = _noop,
    sources: list[PackageSource] | None = None,
) -> dict[str, UpdateResult]:
    """Prüft für alle übergebenen Programme, ob es neuere Versionen gibt.

    Die Quellen werden parallel abgefragt; das Ergebnis ist ein Wörterbuch
    ``Program.key → UpdateResult``. Die Programme selbst werden nicht verändert,
    damit die Oberfläche die Ergebnisse gefahrlos im Hauptthread übernehmen kann.
    """
    sources = sources if sources is not None else all_sources()
    responsible: dict[Source, PackageSource] = {s: src for src in sources for s in src.handles}
    groups: dict[int, tuple[PackageSource, list[Program]]] = {}
    results: dict[str, UpdateResult] = {}
    for p in programs:
        src = responsible.get(p.source)
        if src is None:
            continue
        groups.setdefault(id(src), (src, []))[1].append(p)

    def run(group: tuple[PackageSource, list[Program]]) -> dict[str, UpdateResult]:
        src, progs = group
        progress(f"Prüfe Updates: {src.title} …")
        try:
            return src.check_updates(progs)
        except Exception as exc:
            log.exception("Update-Prüfung %s fehlgeschlagen", src.title)
            return {p.key: UpdateResult(UpdateStatus.UNKNOWN, note=f"Fehler: {exc}") for p in progs}

    with ThreadPoolExecutor(max_workers=4) as pool:
        for partial in pool.map(run, groups.values()):
            results.update(partial)
    progress("Update-Prüfung abgeschlossen.")
    return results


def apply_updates(programs: list[Program], results: dict[str, UpdateResult]) -> None:
    for p in programs:
        if p.key in results:
            p.update = results[p.key]
