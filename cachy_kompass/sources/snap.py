"""Snap-Pakete (unter CachyOS nur, wenn snapd nachinstalliert wurde)."""

from __future__ import annotations

from cachy_kompass import util
from cachy_kompass.i18n import _
from cachy_kompass.models import Program, Source, UpdateResult, UpdateStatus
from cachy_kompass.sources.base import PackageSource, ScanContext

# Laufzeitumgebungen, die Snap im Hintergrund braucht – keine eigenen Programme.
_RUNTIME_PREFIXES = ("core", "snapd", "bare", "gtk-common-themes", "gnome-", "kf5-", "kf6-", "kde-frameworks", "mesa-")


def parse_list(text: str) -> list[dict[str, str]]:
    """``snap list``: Name Version Rev Tracking Publisher Notes."""
    rows = []
    for i, line in enumerate(text.splitlines()):
        parts = line.split()
        if i == 0 or len(parts) < 3:
            continue  # Kopfzeile
        rows.append(
            {
                "name": parts[0],
                "version": parts[1],
                "publisher": parts[4] if len(parts) > 4 else "",
                "notes": parts[5] if len(parts) > 5 else "",
            }
        )
    return rows


def parse_refresh_list(text: str) -> dict[str, str]:
    """``snap refresh --list`` → {Name: neue Version}."""
    result = {}
    for i, line in enumerate(text.splitlines()):
        parts = line.split()
        if i == 0 or len(parts) < 2:
            continue
        result[parts[0]] = parts[1]
    return result


def is_runtime(row: dict[str, str]) -> bool:
    notes = row.get("notes", "")
    return "base" in notes or "snapd" in notes or "core" in notes or row["name"].startswith(_RUNTIME_PREFIXES)


class SnapSource(PackageSource):
    title = "Snap"
    handles = (Source.SNAP,)

    def is_available(self) -> bool:
        return util.which("snap") is not None

    def scan(self, ctx: ScanContext) -> list[Program]:
        programs = []
        for row in parse_list(util.run(["snap", "list"]) or ""):
            name = row["name"]
            programs.append(
                Program(
                    name=name,
                    version=row["version"],
                    source=Source.SNAP,
                    origin=_("Snap Store (Herausgeber: {publisher})").format(publisher=row["publisher"] or "?"),
                    explicit=not is_runtime(row),
                    executables=[f"/snap/bin/{name}"],
                    url=f"https://snapcraft.io/{name}",
                )
            )
        return programs

    def check_updates(self, programs: list[Program]) -> dict[str, UpdateResult]:
        out = util.run(["snap", "refresh", "--list"], timeout=120)
        if out is None:
            return {p.key: UpdateResult(UpdateStatus.UNKNOWN, note=_("Snap Store nicht erreichbar.")) for p in programs}
        updates = parse_refresh_list(out)
        return {
            p.key: UpdateResult(UpdateStatus.OUTDATED, updates[p.name])
            if p.name in updates
            else UpdateResult(UpdateStatus.CURRENT, p.version)
            for p in programs
        }
