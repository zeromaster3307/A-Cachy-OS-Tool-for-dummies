"""Kleine Hilfsfunktionen: Befehle ausführen, Webseiten abfragen, Versionen vergleichen."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import urllib.parse
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from cachy_kompass import APP_ID, __version__, i18n

log = logging.getLogger(__name__)

HOME = Path.home()
USER_AGENT = f"{APP_ID}/{__version__} (+https://github.com/zeromaster3307/A-Cachy-OS-Tool-for-dummies)"


def which(cmd: str) -> str | None:
    """Pfad eines Befehls oder ``None``, falls er nicht installiert ist."""
    return shutil.which(cmd)


def run(
    cmd: list[str],
    timeout: float = 120,
    ok_codes: Iterable[int] = (0,),
) -> str | None:
    """Führt einen Befehl aus und liefert seine Ausgabe.

    Die Sprache wird auf Englisch (``LC_ALL=C``) gestellt, damit sich die
    Ausgabe zuverlässig auswerten lässt. Gibt ``None`` zurück, wenn der Befehl
    fehlt, zu lange braucht oder mit einem unerwarteten Code endet.
    """
    env = dict(os.environ, LC_ALL="C", LANG="C")
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            env=env,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.info("Befehl fehlgeschlagen: %s (%s)", " ".join(cmd), exc)
        return None
    if proc.returncode not in tuple(ok_codes):
        log.info("Befehl %s endete mit Code %s: %s", " ".join(cmd), proc.returncode, proc.stderr.strip())
        return None
    return proc.stdout


def http_json(url: str, timeout: float = 15) -> Any:
    """Lädt JSON von einer Web-Schnittstelle. Wirft eine Ausnahme bei Fehlern."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def url_quote(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def vercmp(a: str, b: str) -> int:
    """Vergleicht zwei Paketversionen wie pacman: <0, 0 oder >0.

    Nutzt das Programm ``vercmp`` aus pacman; ohne pacman (z. B. in Tests)
    wird ein einfacher Vergleich verwendet.
    """
    if a == b:
        return 0
    if which("vercmp"):
        out = run(["vercmp", a, b], timeout=10)
        if out is not None:
            try:
                return int(out.strip())
            except ValueError:
                pass
    return _simple_vercmp(a, b)


def _simple_vercmp(a: str, b: str) -> int:
    import re

    def parts(v: str) -> list[tuple[int, str]]:
        return [(int(p), "") if p.isdigit() else (-1, p) for p in re.findall(r"\d+|[a-zA-Z]+", v)]

    pa, pb = parts(a), parts(b)
    return (pa > pb) - (pa < pb)


_SIZE_UNITS = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3, "TiB": 1024**4}


def parse_size(text: str) -> int:
    """„9.42 MiB“ (wie pacman es schreibt) → Bytes. Unbekanntes → 0."""
    parts = text.replace(",", ".").split()
    if len(parts) != 2 or parts[1] not in _SIZE_UNITS:
        return 0
    try:
        return int(float(parts[0]) * _SIZE_UNITS[parts[1]])
    except ValueError:
        return 0


def format_size(size: int) -> str:
    """Bytes → gut lesbare Größe, z. B. „1,2 GB“ (auf Englisch „1.2 GB“)."""
    value = float(size)
    for unit in ("Bytes", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            text = f"{value:.0f}" if unit in ("Bytes", "KB") or value >= 100 else f"{value:.1f}"
            return f"{i18n.decimal(text)} {unit}"
        value /= 1024
    return f"{size} Bytes"


def folder_size(path: Path) -> int:
    """Gesamtgröße aller Dateien in einem Ordner (unlesbare Dateien werden übersprungen)."""
    total = 0
    for root, _dirs, files in os.walk(path, onerror=lambda e: None):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                pass
    return total


def pacman_owners(paths: Iterable[str]) -> dict[str, str]:
    """Welches pacman-Paket besitzt welche Datei? Nicht erfasste Pfade fehlen im Ergebnis."""
    paths = [p for p in paths]
    if not paths or not which("pacman"):
        return {}
    # pacman -Qo endet mit Code 1, wenn mindestens ein Pfad keinem Paket gehört.
    out = run(["pacman", "-Qo", *paths], timeout=60, ok_codes=(0, 1))
    return parse_pacman_owners(out or "")


def parse_pacman_owners(text: str) -> dict[str, str]:
    """Wertet Zeilen wie ``/usr/bin/foo is owned by foo 1.0-1`` aus."""
    owners: dict[str, str] = {}
    for line in text.splitlines():
        if " is owned by " not in line:
            continue
        path, rest = line.split(" is owned by ", 1)
        pkg = rest.split()[0] if rest.split() else ""
        owners[path.strip().rstrip("/")] = pkg
    return owners


def is_executable_file(path: Path) -> bool:
    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False
