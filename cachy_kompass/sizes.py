"""Wie viel Platz belegt ein Programm?

pacman liefert die Größe direkt („Installed Size“), Flatpak ebenfalls. Für die
übrigen Quellen zählen wir die Dateien im Programmordner zusammen.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from cachy_kompass import util
from cachy_kompass.models import Program, Source

SNAP_DIR = Path("/var/lib/snapd/snaps")

_DECIMAL_UNITS = {"bytes": 1, "b": 1, "kb": 1000, "mb": 1000**2, "gb": 1000**3, "tb": 1000**4}


def parse_decimal_size(text: str) -> int:
    """„52,4 MB“ / „1.2 GB“ / „900 bytes“ (wie Flatpak sie schreibt) → Bytes. Unbekanntes → 0."""
    m = re.match(r"^\s*([\d.,]+)\s*([A-Za-z]+)\s*$", text.replace("\xa0", " "))
    if not m or m.group(2).lower() not in _DECIMAL_UNITS:
        return 0
    try:
        return int(float(m.group(1).replace(",", ".")) * _DECIMAL_UNITS[m.group(2).lower()])
    except ValueError:
        return 0


def _file_size(path: str | Path) -> int:
    try:
        return os.stat(path).st_size
    except OSError:
        return 0


def _path_size(path: str | Path) -> int:
    p = Path(path)
    if p.is_dir():
        return util.folder_size(p)
    return _file_size(p)


def _ancestor_named(path: Path, parent_name: str) -> Path | None:
    """Der Ordner direkt unterhalb eines Ordners namens ``parent_name`` (z. B. Cellar/<name>)."""
    for candidate in [path, *path.parents]:
        if candidate.parent.name == parent_name:
            return candidate
    return None


def estimate(p: Program) -> int:
    """Belegter Platz in Bytes (0 = unbekannt)."""
    if p.size_bytes:
        return p.size_bytes
    if p.source is Source.SNAP:
        # Snap bewahrt mehrere Versionen auf – alle zählen
        return sum(_file_size(f) for f in SNAP_DIR.glob(f"{p.name}_*.snap"))
    if p.source in (Source.APPIMAGE, Source.MANUAL) and p.install_path:
        return _path_size(p.install_path)
    if p.source is Source.PIPX:
        home = Path(os.environ.get("PIPX_HOME") or util.HOME / ".local" / "share" / "pipx")
        return _path_size(home / "venvs" / p.name)
    if p.source is Source.UV:
        home = Path(os.environ.get("UV_TOOL_DIR") or util.HOME / ".local" / "share" / "uv" / "tools")
        return _path_size(home / p.name)
    if p.source is Source.NPM and p.install_path:
        return _path_size(p.install_path)
    if p.source is Source.BREW:
        for exe in p.executables:
            folder = _ancestor_named(Path(os.path.realpath(exe)), "Cellar")
            if folder:
                return _path_size(folder)
    # cargo u. a.: die Programmdateien selbst
    return sum(_file_size(os.path.realpath(x)) for x in p.executables)


def fill_sizes(programs: list[Program]) -> None:
    for p in programs:
        if not p.size_bytes:
            try:
                p.size_bytes = estimate(p)
            except OSError:
                p.size_bytes = 0
