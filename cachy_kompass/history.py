"""Wann wurde was installiert – und ist seit dem letzten Start ein Neustart fällig?

Quelle ist vor allem das Protokoll von pacman (``/var/log/pacman.log``). Dort
steht jede Installation, jedes Update und jedes Entfernen mit Datum, z. B.::

    [2024-10-01T10:00:00+0200] [ALPM] installed firefox (131.0-1)
    [2024-10-05T18:12:44+0200] [ALPM] upgraded linux-cachyos (6.11.1-1 -> 6.11.2-1)

Für andere Quellen (Flatpak, AppImage, …) gibt es kein solches Protokoll. Dort
nehmen wir das Änderungsdatum der Datei bzw. des Ordners – das ist ungefähr das
Installationsdatum (oder das Datum des letzten Updates).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from cachy_kompass import util
from cachy_kompass.models import Program, Source

PACMAN_LOG = Path("/var/log/pacman.log")

_LINE_RE = re.compile(
    r"^\[(?P<ts>[^\]]+)\] \[ALPM\] (?P<action>installed|upgraded|downgraded|reinstalled|removed) "
    r"(?P<pkg>\S+) \((?P<version>[^)]*)\)"
)


@dataclass
class LogEvent:
    when: datetime
    action: str
    package: str
    version: str


def parse_timestamp(text: str) -> datetime | None:
    """„2024-10-01T10:00:00+0200“ oder alt „2019-01-01 10:00“ → datetime (mit Zeitzone)."""
    text = text.strip()
    # Python < 3.11 versteht „+0200“ nicht, nur „+02:00“
    text = re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", text)
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.astimezone()  # alte Einträge ohne Zeitzone: Ortszeit
    return when


def parse_log(text: str) -> list[LogEvent]:
    events = []
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        when = parse_timestamp(m.group("ts"))
        if when is not None:
            events.append(LogEvent(when, m.group("action"), m.group("pkg"), m.group("version")))
    return events


def read_log(path: Path = PACMAN_LOG) -> list[LogEvent]:
    try:
        return parse_log(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return []


def install_dates(events: list[LogEvent]) -> dict[str, datetime]:
    """Paket → Datum der (letzten) Installation. Updates zählen nicht als Installation."""
    dates: dict[str, datetime] = {}
    for e in events:
        if e.action == "installed":
            dates[e.package] = e.when
    return dates


# --- Installationsdatum für alle Programme ---------------------------------------


def _mtime(path: str | Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(os.lstat(path).st_mtime, tz=timezone.utc).astimezone()
    except (OSError, ValueError):
        return None


def _flatpak_app_dir(p: Program) -> Path:
    if p.installation == "user":
        return util.HOME / ".local" / "share" / "flatpak" / "app" / p.name
    return Path("/var/lib/flatpak/app") / p.name


def fill_install_dates(programs: list[Program], events: list[LogEvent]) -> None:
    """Setzt ``installed_at`` für alle Programme (soweit herauszufinden)."""
    from_log = install_dates(events)
    for p in programs:
        if p.source in (Source.REPO, Source.AUR):
            if p.name in from_log:
                p.installed_at = from_log[p.name]
            continue
        if p.source is Source.FLATPAK:
            path: str | Path | None = _flatpak_app_dir(p)
        elif p.source is Source.SNAP:
            path = Path("/snap") / p.name
        elif p.source in (Source.APPIMAGE, Source.MANUAL) and p.install_path:
            path = p.install_path
        elif p.executables:
            path = p.executables[0]
        else:
            path = None
        if path is not None:
            p.installed_at = _mtime(path)
            p.installed_approx = p.installed_at is not None


# --- Neustart nötig? ---------------------------------------------------------------

#: Pakete, deren Update erst nach einem Neustart wirkt
REBOOT_EXACT = {
    "systemd", "glibc", "amd-ucode", "intel-ucode", "mesa", "lib32-mesa", "dbus", "dbus-broker",
    "linux-firmware",
}
REBOOT_PREFIXES = ("linux", "nvidia")
_NOT_REBOOT_SUFFIXES = ("-headers", "-docs", "-api-headers")


def needs_reboot_for(package: str) -> bool:
    if package.endswith(_NOT_REBOOT_SUFFIXES):
        return False
    if package in REBOOT_EXACT:
        return True
    # „linux“, „linux-cachyos“, „linux-lts“, „nvidia-utils“ … – Werkzeuge ohne Treiber ausgenommen
    return package.startswith(REBOOT_PREFIXES) and not package.startswith(("linuxdeploy", "nvidia-settings"))


def boot_time() -> datetime | None:
    """Zeitpunkt des letzten Systemstarts (aus /proc/stat)."""
    try:
        for line in Path("/proc/stat").read_text().splitlines():
            if line.startswith("btime "):
                return datetime.fromtimestamp(int(line.split()[1]), tz=timezone.utc)
    except (OSError, ValueError):
        pass
    return None


@dataclass
class RebootInfo:
    #: Läuft noch ein Kernel, dessen Dateien schon ersetzt wurden?
    kernel_replaced: bool = False
    #: Wichtige Pakete, die seit dem Start aktualisiert wurden
    packages: list[str] = field(default_factory=list)

    @property
    def needed(self) -> bool:
        return self.kernel_replaced or bool(self.packages)

    def message(self) -> str:
        if not self.needed:
            return ""
        parts = []
        if self.kernel_replaced:
            parts.append("Der Kernel wurde aktualisiert – der laufende ist noch der alte.")
        if self.packages:
            shown = ", ".join(self.packages[:6]) + (" …" if len(self.packages) > 6 else "")
            parts.append(f"Seit dem letzten Start aktualisiert: {shown}.")
        return " ".join(parts)


def check_reboot(
    events: list[LogEvent],
    booted: datetime | None,
    kernel_release: str | None = None,
    modules_dir: Path = Path("/usr/lib/modules"),
) -> RebootInfo:
    info = RebootInfo()
    if kernel_release is None:
        kernel_release = os.uname().release
    # Klassischer Test unter Arch: Nach einem Kernel-Update fehlt der Modulordner
    # des laufenden Kernels (er wurde durch den neuen ersetzt).
    if kernel_release and modules_dir.is_dir() and not (modules_dir / kernel_release).is_dir():
        info.kernel_replaced = True
    if booted is not None:
        seen: set[str] = set()
        for e in events:
            if e.when > booted and e.action in ("upgraded", "downgraded", "reinstalled"):
                if needs_reboot_for(e.package) and e.package not in seen:
                    seen.add(e.package)
                    info.packages.append(e.package)
    return info
