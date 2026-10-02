"""Programme ohne Paketverwaltung: AppImages und von Hand kopierte Programme."""

from __future__ import annotations

import os
import re
from pathlib import Path

from cachy_kompass import util
from cachy_kompass.models import Program, Source
from cachy_kompass.sources.base import PackageSource, ScanContext

HOME = util.HOME

# Typische Ablageorte für AppImages (Gear Lever nutzt ~/AppImages,
# AppImageLauncher ~/Applications).
APPIMAGE_DIRS = [
    HOME / "Applications",
    HOME / "AppImages",
    HOME / "Apps",
    HOME / ".local" / "bin",
    HOME / "Downloads",
    HOME / "Desktop",
    HOME / "Schreibtisch",
    HOME / "bin",
    Path("/opt"),
]
APPIMAGE_DEPTH = 2

# Ordner, in denen Programme gern von Hand abgelegt werden.
MANUAL_BIN_DIRS = [HOME / ".local" / "bin", HOME / "bin", Path("/usr/local/bin"), HOME / "go" / "bin"]

# Ziele von Verknüpfungen, die bereits eine andere Quelle verwaltet.
MANAGED_PREFIXES = [
    str(HOME / ".local" / "share" / "pipx"),
    str(HOME / ".local" / "pipx"),
    str(HOME / ".local" / "share" / "uv"),
    str(HOME / ".cargo"),
    "/home/linuxbrew",
    str(HOME / ".linuxbrew"),
    "/usr/lib/node_modules",
    "/usr/local/lib/node_modules",
    str(HOME / ".npm-global"),
    str(HOME / ".local" / "lib" / "node_modules"),
    str(HOME / ".nix-profile"),
    "/nix/",
    "/snap/",
    "/var/lib/flatpak",
    str(HOME / ".local" / "share" / "flatpak"),
]

_APPIMAGE_NAME_RE = re.compile(
    r"^(?P<name>.+?)(?:[-_ ]v?(?P<version>\d[\w.+~]*?))?(?:[-_.](?:x86[-_]64|amd64|aarch64|arm64|linux|x64))*$",
    re.IGNORECASE,
)


def split_appimage_name(filename: str) -> tuple[str, str]:
    """``Obsidian-1.6.7.AppImage`` → (``Obsidian``, ``1.6.7``)."""
    stem = re.sub(r"\.appimage$", "", filename, flags=re.IGNORECASE)
    m = _APPIMAGE_NAME_RE.match(stem)
    if not m:
        return stem, ""
    return m.group("name").strip("-_ ") or stem, m.group("version") or ""


def find_appimages(dirs: list[Path], depth: int = APPIMAGE_DEPTH) -> list[Path]:
    found: dict[str, Path] = {}
    for base in dirs:
        if not base.is_dir():
            continue
        base_depth = len(base.parts)
        for root, subdirs, files in os.walk(base, onerror=lambda e: None):
            if len(Path(root).parts) - base_depth >= depth:
                subdirs[:] = []
            subdirs[:] = [d for d in subdirs if not d.startswith(".")]
            for f in files:
                if f.lower().endswith(".appimage"):
                    path = Path(root) / f
                    found.setdefault(str(path.resolve()), path)
    return sorted(found.values())


class AppImageSource(PackageSource):
    title = "AppImages"
    handles = (Source.APPIMAGE,)

    def is_available(self) -> bool:
        return True

    def scan(self, ctx: ScanContext) -> list[Program]:
        programs = []
        for path in find_appimages(APPIMAGE_DIRS):
            name, version = split_appimage_name(path.name)
            programs.append(
                Program(
                    name=name,
                    version=version or "?",
                    source=Source.APPIMAGE,
                    origin=f"Datei {path}",
                    executables=[str(path)],
                    install_path=str(path),
                )
            )
        return programs


def _is_managed_elsewhere(path: Path, known: set[str]) -> bool:
    if str(path) in known or path.name.lower().endswith(".appimage"):
        return True
    try:
        target = str(path.resolve())
    except OSError:
        return False
    return target in known or any(target.startswith(prefix) for prefix in MANAGED_PREFIXES)


class ManualSource(PackageSource):
    """Findet Programme, die keiner Paketverwaltung gehören.

    Sucht in ~/.local/bin, ~/bin, ~/go/bin, /usr/local/bin und den Unterordnern
    von /opt. Muss als letzte Quelle laufen, damit bekannte Programme
    (z. B. Verknüpfungen von pipx) übersprungen werden.
    """

    title = "Manuell installierte Programme"
    handles = (Source.MANUAL,)

    def is_available(self) -> bool:
        return True

    def scan(self, ctx: ScanContext) -> list[Program]:
        known = ctx.known_executables()
        candidates: list[tuple[Path, str]] = []

        for bin_dir in MANUAL_BIN_DIRS:
            if not bin_dir.is_dir():
                continue
            for entry in sorted(bin_dir.iterdir()):
                if util.is_executable_file(entry) and not _is_managed_elsewhere(entry, known):
                    hint = "vermutlich über „go install“" if bin_dir.name == "bin" and bin_dir.parent.name == "go" else ""
                    candidates.append((entry, hint))

        opt = Path("/opt")
        if opt.is_dir():
            for entry in sorted(opt.iterdir()):
                if entry.is_dir() and not any(str(entry.resolve()).startswith(p) for p in MANAGED_PREFIXES):
                    candidates.append((entry, "Programmordner in /opt"))

        # Alles, was doch einem pacman-Paket gehört, fliegt raus.
        owned = util.pacman_owners(str(p) for p, _ in candidates)
        programs = []
        for path, hint in candidates:
            if str(path) in owned:
                continue
            exes = [str(path)] if path.is_file() else _find_main_executable(path)
            programs.append(
                Program(
                    name=path.name,
                    version="?",
                    source=Source.MANUAL,
                    origin=f"{path}" + (f" ({hint})" if hint else ""),
                    executables=exes,
                    install_path=str(path),
                )
            )
        return programs


def _find_main_executable(folder: Path) -> list[str]:
    """Rät die Hauptprogrammdatei in einem /opt-Ordner (gleichnamig oder in bin/)."""
    candidates = [folder / folder.name, folder / folder.name.lower(), folder / "bin" / folder.name.lower()]
    exes = [str(c) for c in candidates if util.is_executable_file(c)]
    bin_dir = folder / "bin"
    if not exes and bin_dir.is_dir():
        exes = [str(f) for f in sorted(bin_dir.iterdir()) if util.is_executable_file(f)][:5]
    if not exes:
        try:
            exes = [str(f) for f in sorted(folder.iterdir()) if util.is_executable_file(f) and "." not in f.name][:5]
        except OSError:
            pass
    return exes
