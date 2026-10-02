"""Textausgabe im Terminal – praktisch zum Testen oder für Fortgeschrittene."""

from __future__ import annotations

import json
import sys

from cachy_kompass import scanner
from cachy_kompass.models import Program


def _row(p: Program) -> list[str]:
    return [
        p.display_name,
        p.version,
        p.info.label,
        p.menu_status.value,
        p.info.auto_update.value,
        p.update.status.value + (f" ({p.update.latest})" if p.update.latest and p.update.latest != p.version else ""),
    ]


def print_table(programs: list[Program]) -> None:
    header = ["Programm", "Version", "Quelle", "Startmenü", "Auto-Update", "Aktuell?"]
    rows = [header] + [_row(p) for p in programs]
    widths = [min(max(len(r[i]) for r in rows), 40) for i in range(len(header))]
    for n, row in enumerate(rows):
        print("  ".join(cell[: widths[i]].ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
        if n == 0:
            print("  ".join("-" * w for w in widths))


def to_json(programs: list[Program]) -> str:
    return json.dumps(
        [
            {
                "name": p.name,
                "display_name": p.display_name,
                "version": p.version,
                "source": p.source.value,
                "origin": p.origin,
                "explicit": p.explicit,
                "description": p.description,
                "menu": p.menu_status.value,
                "desktop_files": [str(e.path) for e in p.desktop_entries],
                "auto_update": p.info.auto_update.value,
                "update_status": p.update.status.value,
                "latest_version": p.update.latest,
                "executables": p.executables,
                "uninstall": p.uninstall_command(),
            }
            for p in programs
        ],
        indent=2,
        ensure_ascii=False,
    )


def run_cli(show_all: bool, updates: bool, as_json: bool, show_installers: bool) -> int:
    def progress(msg: str) -> None:
        print(msg, file=sys.stderr)

    result = scanner.scan(progress)
    programs = [p for p in result.programs if show_all or p.explicit]
    if updates:
        scanner.apply_updates(programs, scanner.check_updates(programs, progress))

    if as_json:
        print(to_json(programs))
        return 0

    if show_installers:
        print("\nGefundene Paketverwaltungen und App-Stores:\n")
        for inst in result.installers:
            if inst.present:
                count = f" – {inst.program_count} Programme" if inst.program_count is not None else ""
                print(f"  ✔ {inst.spec.name} ({inst.spec.kind}){count}")
        print()

    print_table(programs)
    for w in result.warnings:
        print(f"Warnung: {w}", file=sys.stderr)
    return 0
