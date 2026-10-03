"""Aufräumen: Was belegt unnötig Platz oder ist kaputt?

Jede Prüfung liefert einen „Fund“ (``CleanupItem``) mit verständlicher
Erklärung, der Liste der betroffenen Dinge, dem Platz, den man gewinnt, und –
falls sinnvoll – einer Aufräum-Aktion.

Grundsätze wie überall im Software-Kompass:
  * Die Prüfungen selbst verändern nichts (nur lesen, „Trockenlauf“).
  * Was Administratorrechte braucht, läuft sichtbar im Terminal (``terminal.py``);
    pacman, paccache und flatpak fragen dort vor dem Löschen noch einmal nach.
  * Was riskant ist (z. B. Pakete, die nicht mehr im AUR stehen), bekommt keinen
    Knopf, sondern nur Erklärung und Befehl – die Entscheidung bleibt beim Nutzer.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from cachy_kompass import desktop, util
from cachy_kompass.models import DesktopEntry, Program, Source
from cachy_kompass.sources.pacman import AUR_RPC

PACMAN_CACHE = Path("/var/cache/pacman/pkg")
AUR_BUILD_CACHES = [util.HOME / ".cache" / "paru" / "clone", util.HOME / ".cache" / "yay"]
#: So viele Versionen jedes Pakets behält paccache (für den Notfall-Rückweg)
KEEP_VERSIONS = 2


class Action(Enum):
    TERMINAL = "terminal"            # Befehle sichtbar im Terminal ausführen
    REMOVE_ENTRIES = "remove_entries"  # Startmenü-Einträge im Benutzerordner löschen
    NONE = "none"                    # nur Hinweis, kein Knopf


@dataclass
class CleanupItem:
    key: str
    title: str
    explanation: str
    #: Kurzfassung für die Tabelle, z. B. „12 Pakete“
    summary: str
    #: Die betroffenen Dinge (Paketnamen, Pfade …)
    details: list[str] = field(default_factory=list)
    #: Platz, den man gewinnt (Bytes, 0 = unbekannt/keiner)
    size: int = 0
    action: Action = Action.NONE
    #: Bei ``Action.TERMINAL``: auszuführende Befehle
    commands: list[list[str]] = field(default_factory=list)
    #: Bei ``Action.REMOVE_ENTRIES``: zu löschende Einträge
    entries: list[DesktopEntry] = field(default_factory=list)
    #: Zusätzliche Warnung, die vor dem Aufräumen angezeigt wird
    warning: str = ""
    #: Befehl zum Kopieren, wenn es keinen Knopf gibt
    manual_command: str = ""

    @property
    def found(self) -> bool:
        """Gibt es hier etwas zu tun?"""
        return bool(self.details or self.size or self.entries)


Progress = Callable[[str], None]


def count(n: int, one: str, many: str) -> str:
    """„1 Paket“, „3 Pakete“, „keine“."""
    if n == 0:
        return "keine"
    return f"{n} {one if n == 1 else many}"


# --- Verwaiste Pakete ------------------------------------------------------------


def check_orphans(programs: list[Program]) -> CleanupItem | None:
    if not util.which("pacman"):
        return None
    # Code 1 heißt hier „keine gefunden“.
    names = (util.run(["pacman", "-Qdtq"], ok_codes=(0, 1)) or "").split()
    sizes = {p.name: p.size_bytes for p in programs if p.source in (Source.REPO, Source.AUR)}
    total = sum(sizes.get(n, 0) for n in names)
    return CleanupItem(
        key="orphans",
        title="Verwaiste Pakete",
        explanation=(
            "Pakete, die einmal automatisch als Abhängigkeit für ein anderes Programm "
            "mitinstalliert wurden. Dieses Programm ist inzwischen weg – die Abhängigkeit "
            "braucht niemand mehr. Sie zu entfernen ist normalerweise gefahrlos."
        ),
        summary=count(len(names), "Paket", "Pakete"),
        details=[f"{n}  ({util.format_size(sizes[n])})" if sizes.get(n) else n for n in names],
        size=total,
        action=Action.TERMINAL if names else Action.NONE,
        commands=[["sudo", "pacman", "-Rns", *names]] if names else [],
        warning=(
            "pacman zeigt vor dem Löschen die vollständige Liste und fragt noch einmal nach. "
            "Wenn du ein Paket davon bewusst behalten willst, brich dort ab (n). "
            "Nach dem Aufräumen können weitere verwaiste Pakete auftauchen – einfach erneut prüfen."
        ),
    )


# --- Paket-Zwischenspeicher --------------------------------------------------------

_DRY_RUN_RE = re.compile(r"(\d+)\s+candidates?.*?saved:\s*([\d.,]+\s*\w+)", re.IGNORECASE)


def parse_paccache_dry_run(text: str) -> tuple[int, int]:
    """Trockenlauf von paccache → (Anzahl Dateien, Bytes). Nichts gefunden → (0, 0)."""
    m = _DRY_RUN_RE.search(text)
    if not m:
        return 0, 0
    return int(m.group(1)), util.parse_size(m.group(2))


def check_package_cache() -> CleanupItem | None:
    if not PACMAN_CACHE.is_dir():
        return None
    total = util.folder_size(PACMAN_CACHE)
    explanation = (
        "pacman bewahrt jede heruntergeladene Paketversion in „/var/cache/pacman/pkg“ auf. "
        "Das ist praktisch, um nach einem fehlerhaften Update zur vorigen Version zurückzukehren, "
        f"wächst aber mit der Zeit auf viele Gigabyte. Aufräumen behält die {KEEP_VERSIONS} neuesten "
        "Versionen jedes installierten Pakets und entfernt die von deinstallierten Paketen."
    )
    item = CleanupItem(
        key="pkgcache",
        title="Paket-Zwischenspeicher",
        explanation=explanation,
        summary=f"belegt {util.format_size(total)}",
    )
    if not util.which("paccache"):
        item.explanation += " (Zum Aufräumen wird das Paket „pacman-contrib“ benötigt.)"
        item.manual_command = "sudo pacman -S pacman-contrib"
        return item
    # Trockenläufe („-d“) – zeigen nur, was gelöscht würde, ohne root.
    old_n, old_size = parse_paccache_dry_run(util.run(["paccache", "-d", f"-k{KEEP_VERSIONS}"], ok_codes=(0, 1)) or "")
    gone_n, gone_size = parse_paccache_dry_run(util.run(["paccache", "-du", "-k0"], ok_codes=(0, 1)) or "")
    if old_n:
        item.details.append(f"{old_n} ältere Versionen installierter Pakete ({util.format_size(old_size)})")
    if gone_n:
        item.details.append(f"{gone_n} Dateien deinstallierter Pakete ({util.format_size(gone_size)})")
    item.size = old_size + gone_size
    if item.size:
        item.summary = f"{util.format_size(item.size)} frei machbar (von {util.format_size(total)})"
        item.action = Action.TERMINAL
        item.commands = [["sudo", "paccache", "-r", f"-k{KEEP_VERSIONS}"], ["sudo", "paccache", "-ru", "-k0"]]
    else:
        item.summary = f"aufgeräumt ({util.format_size(total)})"
    return item


# --- AUR-Bauordner ---------------------------------------------------------------


def check_aur_build_cache() -> CleanupItem | None:
    folders = [f for f in AUR_BUILD_CACHES if f.is_dir()]
    if not folders:
        return None
    sizes = {f: util.folder_size(f) for f in folders}
    total = sum(sizes.values())
    return CleanupItem(
        key="aurcache",
        title="AUR-Bauordner",
        explanation=(
            "Beim Installieren aus dem AUR laden paru bzw. yay den Quellcode herunter und bauen "
            "das Programm in diesen Ordnern. Danach werden sie nicht mehr gebraucht – beim "
            "nächsten Update wird einfach neu heruntergeladen. Löschen ist gefahrlos."
        ),
        summary=f"{util.format_size(total)}" if total else "leer",
        details=[f"{f}  ({util.format_size(s)})" for f, s in sizes.items() if s],
        size=total,
        action=Action.TERMINAL if total else Action.NONE,
        # Liegt im eigenen Benutzerordner – kein sudo nötig.
        commands=[["rm", "-rf", *[str(f) for f, s in sizes.items() if s]]] if total else [],
    )


# --- Flatpak ---------------------------------------------------------------------


def check_flatpak_unused() -> CleanupItem | None:
    if not util.which("flatpak"):
        return None
    return CleanupItem(
        key="flatpak",
        title="Unbenutzte Flatpak-Laufzeiten",
        explanation=(
            "Flatpak-Apps brauchen „Laufzeiten“ (Bibliothekspakete wie GNOME oder KDE Platform). "
            "Wird eine App entfernt oder aktualisiert, bleiben alte Laufzeiten oft liegen – nicht "
            "selten mehrere Gigabyte. Was genau unbenutzt ist, ermittelt Flatpak selbst: Es zeigt "
            "im Terminal die Liste an und fragt vor dem Löschen nach."
        ),
        summary="im Terminal prüfen",
        details=["Flatpak zeigt die gefundenen Laufzeiten im Terminal an."],
        action=Action.TERMINAL,
        commands=[["flatpak", "uninstall", "--unused"], ["flatpak", "uninstall", "--user", "--unused"]],
    )


# --- Kaputte Startmenü-Einträge -----------------------------------------------------


def check_broken_entries(entries: list[DesktopEntry], helper_names: Collection[str] = ()) -> CleanupItem:
    def missing(e: DesktopEntry) -> str:
        return desktop.missing_program(e.exec, helper_names)

    candidates = [e for e in entries if e.type == "Application" and e.exec and missing(e)]
    removable = [e for e in candidates if desktop.can_remove(e)]
    # Versteckte Systemeinträge (z. B. KDE-Hintergrunddienste wie „KIO“) sieht man
    # weder im Startmenü noch kann man sie hier entfernen – sie gehören nicht in
    # die Aufräum-Liste. Sichtbare kaputte Systemeinträge sind dagegen ein
    # nützlicher Hinweis (Menüpunkt, der nichts tut).
    system = [e for e in candidates if not desktop.can_remove(e) and e.visible]
    broken = removable + system
    details = [f"{e.name}  –  fehlt: {missing(e)}  ({e.path})" for e in removable]
    details += [
        f"{e.name}  –  fehlt: {missing(e)}  – Systemeintrag, nur Hinweis  ({e.path})"
        for e in system
    ]
    explanation = (
        "Diese Einträge zeigen auf ein Programm, das es nicht (mehr) gibt – meist Reste von "
        "deinstallierten Programmen oder AppImages, die verschoben wurden. Einträge in deinem "
        "Benutzerordner können direkt entfernt werden."
    )
    if system:
        explanation += (
            " Systemeinträge gehören zu einem installierten Paket und werden nicht angefasst – "
            "dort fehlt meist nur ein optionales Zusatzprogramm, oder das Paket ist fehlerhaft "
            "und wird mit dem nächsten Update repariert."
        )
    return CleanupItem(
        key="entries",
        title="Kaputte Startmenü-Einträge",
        explanation=explanation,
        summary=count(len(broken), "Eintrag", "Einträge"),
        details=details,
        action=Action.REMOVE_ENTRIES if removable else Action.NONE,
        entries=removable,
        warning="Entfernt werden nur die Einträge in deinem Benutzerordner, nicht die Programme selbst.",
    )


# --- Nicht mehr im AUR -------------------------------------------------------------


def check_not_in_aur(programs: list[Program]) -> CleanupItem | None:
    aur = sorted(p.name for p in programs if p.source is Source.AUR)
    if not aur:
        return None
    found: set[str] = set()
    try:
        for i in range(0, len(aur), 100):
            chunk = aur[i : i + 100]
            query = "&".join(f"arg[]={util.url_quote(n)}" for n in chunk)
            found |= {r["Name"] for r in util.http_json(f"{AUR_RPC}?{query}").get("results", [])}
    except Exception:
        return CleanupItem(
            key="aur",
            title="Nicht mehr im AUR",
            explanation="Das AUR war nicht erreichbar – bitte später erneut prüfen.",
            summary="nicht prüfbar",
        )
    missing = [n for n in aur if n not in found]
    return CleanupItem(
        key="aur",
        title="Nicht mehr im AUR",
        explanation=(
            "Diese Pakete wurden aus dem AUR installiert, stehen dort aber nicht mehr. Sie bekommen "
            "deshalb keine Updates mehr. Häufige Gründe: Das Programm ist inzwischen in einem "
            "offiziellen Repo (dann besser von dort installieren), wurde umbenannt oder eingestellt. "
            "Manche Pakete hast du vielleicht auch selbst gebaut – dann ist alles in Ordnung. "
            "Deshalb gibt es hier keinen Aufräum-Knopf: Prüfe selbst, ob du sie noch brauchst."
        ),
        summary=count(len(missing), "Paket", "Pakete"),
        details=missing,
        manual_command=f"sudo pacman -Rns {' '.join(missing)}" if missing else "",
    )


# --- Doppelt installiert -----------------------------------------------------------


def check_duplicates(groups: list[list[Program]]) -> CleanupItem:
    details = []
    for group in groups:
        variants = "  +  ".join(f"{p.display_name} ({p.info.label})" for p in group)
        commands = "   |   ".join(p.uninstall_command() for p in group)
        details.append(f"{variants}  –  entfernen mit: {commands}")
    return CleanupItem(
        key="duplicates",
        title="Doppelt installiert",
        explanation=(
            "Diese Programme sind mehrfach installiert – aus verschiedenen Quellen, z. B. aus dem "
            "Repo und zusätzlich als Flatpak. Das passiert leicht, wenn man verschiedenen "
            "Anleitungen folgt. Es kostet Platz, und im Startmenü stehen dann oft zwei Einträge, "
            "die unterschiedliche Versionen und Einstellungen haben. Meist ist die Fassung aus dem "
            "offiziellen Repo die beste Wahl (wird mit dem Systemupdate aktuell gehalten). "
            "Die Erkennung läuft über den Namen – prüfe also selbst, ob es wirklich dasselbe "
            "Programm ist. Deshalb gibt es hier keinen Aufräum-Knopf. Die Befehle zum Entfernen "
            "findest du auch im Reiter „Programme“ beim jeweiligen Programm."
        ),
        summary=count(len(groups), "Programm", "Programme"),
        details=details,
    )


# --- Alles zusammen ----------------------------------------------------------------


def _noop(_: str) -> None:
    pass


def scan(
    programs: list[Program],
    entries: list[DesktopEntry],
    helper_names: Collection[str] = (),
    progress: Progress = _noop,
    duplicate_groups: list[list[Program]] | None = None,
) -> list[CleanupItem]:
    """Führt alle Prüfungen aus. Ändert nichts am System."""
    checks: list[tuple[str, Callable[[], CleanupItem | None]]] = [
        ("verwaiste Pakete", lambda: check_orphans(programs)),
        ("Paket-Zwischenspeicher", check_package_cache),
        ("AUR-Bauordner", check_aur_build_cache),
        ("Flatpak", check_flatpak_unused),
        ("Startmenü-Einträge", lambda: check_broken_entries(entries, helper_names)),
        ("doppelte Programme", lambda: check_duplicates(duplicate_groups or [])),
        ("AUR (braucht Internet)", lambda: check_not_in_aur(programs)),
    ]
    items = []
    for label, check in checks:
        progress(f"Prüfe {label} …")
        try:
            item = check()
        except Exception as exc:  # eine fehlerhafte Prüfung soll die anderen nicht stoppen
            item = CleanupItem(key=label, title=label, explanation=f"Prüfung fehlgeschlagen: {exc}", summary="Fehler")
        if item is not None:
            items.append(item)
    progress("Prüfung abgeschlossen.")
    return items
