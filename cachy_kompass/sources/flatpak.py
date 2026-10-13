"""Flatpak-Anwendungen (meist von Flathub)."""

from __future__ import annotations

from cachy_kompass import sizes, util
from cachy_kompass.i18n import _
from cachy_kompass.models import Program, Source, UpdateResult, UpdateStatus
from cachy_kompass.sources.base import PackageSource, ScanContext

COLUMNS = "application,name,version,branch,origin,installation,size"


def parse_list(text: str) -> list[dict[str, str]]:
    """``flatpak list --app --columns=…`` (tabulatorgetrennt) auswerten."""
    keys = COLUMNS.split(",")
    rows = []
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) < 2 or cols[0] in {"Application ID", "Application"}:
            continue
        cols += [""] * (len(keys) - len(cols))
        rows.append(dict(zip(keys, (c.strip() for c in cols))))
    return rows


def parse_updates(text: str) -> dict[str, str]:
    """``flatpak remote-ls --updates --app --columns=application,version``."""
    result = {}
    for line in text.splitlines():
        cols = line.split("\t")
        if cols and cols[0] and cols[0] != "Application ID":
            result[cols[0].strip()] = cols[1].strip() if len(cols) > 1 else ""
    return result


class FlatpakSource(PackageSource):
    title = "Flatpak"
    handles = (Source.FLATPAK,)

    def is_available(self) -> bool:
        return util.which("flatpak") is not None

    def scan(self, ctx: ScanContext) -> list[Program]:
        out = util.run(["flatpak", "list", "--app", f"--columns={COLUMNS}"]) or ""
        programs = []
        for row in parse_list(out):
            app_id = row["application"]
            programs.append(
                Program(
                    name=app_id,
                    display_name=row.get("name") or app_id,
                    version=row.get("version") or row.get("branch") or "",
                    source=Source.FLATPAK,
                    origin=_("Flatpak-Quelle „{remote}“ ({installation})").format(
                        remote=row.get("origin") or "?", installation=row.get("installation") or "system"
                    ),
                    installation=row.get("installation", ""),
                    size_bytes=sizes.parse_decimal_size(row.get("size", "")),
                    url=f"https://flathub.org/apps/{app_id}" if row.get("origin") == "flathub" else "",
                )
            )
        return programs

    def check_updates(self, programs: list[Program]) -> dict[str, UpdateResult]:
        out = util.run(
            ["flatpak", "remote-ls", "--updates", "--app", "--columns=application,version"],
            timeout=180,
        )
        if out is None:
            return {p.key: UpdateResult(UpdateStatus.UNKNOWN, note=_("Flathub nicht erreichbar.")) for p in programs}
        updates = parse_updates(out)
        return {
            p.key: UpdateResult(UpdateStatus.OUTDATED, updates[p.name] or "neuer")
            if p.name in updates
            else UpdateResult(UpdateStatus.CURRENT, p.version)
            for p in programs
        }
