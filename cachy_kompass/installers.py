"""Welche Paketverwaltungen, App-Stores und Update-Werkzeuge sind vorhanden?

Viele Anleitungen im Netz sagen „installiere erst X, dann Y“. Diese Übersicht
zeigt, welche dieser Werkzeuge auf dem System gelandet sind.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cachy_kompass import util
from cachy_kompass.models import Program, Source
from cachy_kompass.sources.devtools import find_brew


@dataclass(frozen=True)
class InstallerSpec:
    name: str
    kind: str
    description: str
    binaries: tuple[str, ...] = ()
    pacman_packages: tuple[str, ...] = ()
    flatpak_ids: tuple[str, ...] = ()
    source: Source | None = None  # zugehörige Quelle (für die Anzahl der Programme)


@dataclass
class InstallerStatus:
    spec: InstallerSpec
    present: bool
    program_count: int | None = None
    found_via: list[str] = field(default_factory=list)


KIND_PM = "Paketverwaltung"
KIND_GUI = "Grafischer App-Store"
KIND_UPDATE = "Update-Werkzeug"
KIND_APPIMAGE = "AppImage-Helfer"

SPECS: list[InstallerSpec] = [
    InstallerSpec("pacman", KIND_PM, "Die Paketverwaltung von Arch Linux und CachyOS. Immer vorhanden.",
                  binaries=("pacman",), source=Source.REPO),
    InstallerSpec("paru", KIND_PM, "AUR-Helfer, bei CachyOS vorinstalliert. Installiert Programme aus dem AUR und aktualisiert Repo- und AUR-Pakete gemeinsam.",
                  binaries=("paru",), source=Source.AUR),
    InstallerSpec("yay", KIND_PM, "Weit verbreiteter AUR-Helfer, wird in vielen Anleitungen nachinstalliert.",
                  binaries=("yay",), source=Source.AUR),
    InstallerSpec("pikaur / trizen", KIND_PM, "Weitere AUR-Helfer.", binaries=("pikaur", "trizen"), source=Source.AUR),
    InstallerSpec("Flatpak", KIND_PM, "Abgeschottete Apps aus Flathub. Unabhängig von pacman.",
                  binaries=("flatpak",), source=Source.FLATPAK),
    InstallerSpec("Snap (snapd)", KIND_PM, "Paketsystem von Ubuntu. Unter CachyOS nicht vorgesehen, meist aus dem AUR nachinstalliert.",
                  binaries=("snap",), source=Source.SNAP),
    InstallerSpec("pipx", KIND_PM, "Installiert Python-Programme in eigene Umgebungen.", binaries=("pipx",), source=Source.PIPX),
    InstallerSpec("uv", KIND_PM, "Schneller Python-Paketmanager, kann mit „uv tool“ Programme installieren.",
                  binaries=("uv",), source=Source.UV),
    InstallerSpec("pip (Python)", KIND_PM, "Python-Paketinstaller. Unter CachyOS sollte er nicht systemweit genutzt werden – besser pipx oder pacman.",
                  binaries=("pip", "pip3")),
    InstallerSpec("cargo (Rust)", KIND_PM, "Baut Rust-Programme aus dem Quellcode.", binaries=("cargo",), source=Source.CARGO),
    InstallerSpec("npm (Node.js)", KIND_PM, "Paketverwaltung für JavaScript/Node.js.", binaries=("npm",), source=Source.NPM),
    InstallerSpec("Homebrew", KIND_PM, "Paketverwaltung aus der macOS-Welt, gibt es auch für Linux.", source=Source.BREW),
    InstallerSpec("Nix", KIND_PM, "Eigenständige Paketverwaltung mit eigenem Paketbestand. (Programme daraus werden noch nicht einzeln aufgelistet.)",
                  binaries=("nix", "nix-env")),
    InstallerSpec("Distrobox", KIND_PM, "Startet andere Linux-Systeme (z. B. Ubuntu) im Container. Programme darin werden hier nicht erfasst.",
                  binaries=("distrobox",)),
    InstallerSpec("go", KIND_PM, "Programmiersprache Go; „go install“ legt Programme in ~/go/bin ab.", binaries=("go",)),
    InstallerSpec("CachyOS Package Installer", KIND_GUI, "Grafisches Programm von CachyOS zum Installieren beliebter Software aus den Repos.",
                  pacman_packages=("cachyos-packageinstaller",), source=Source.REPO),
    InstallerSpec("CachyOS Hello", KIND_GUI, "Willkommens-App von CachyOS mit Abkürzungen zu Software und Einstellungen.",
                  pacman_packages=("cachyos-hello",)),
    InstallerSpec("Octopi", KIND_GUI, "Grafische Oberfläche für pacman (und AUR).", pacman_packages=("octopi",)),
    InstallerSpec("Pamac", KIND_GUI, "App-Store von Manjaro, oft aus dem AUR nachinstalliert. Kann Repo, AUR und Flatpak.",
                  pacman_packages=("pamac-aur", "pamac-all", "pamac-gtk", "pamac-gtk3", "pamac-cli")),
    InstallerSpec("Discover", KIND_GUI, "App-Store von KDE Plasma. Kann Repo-Pakete und Flatpaks installieren und aktualisieren.",
                  pacman_packages=("discover",)),
    InstallerSpec("GNOME Software", KIND_GUI, "App-Store von GNOME. Kann Repo-Pakete und Flatpaks installieren.",
                  pacman_packages=("gnome-software",)),
    InstallerSpec("Bauh", KIND_GUI, "Grafische Oberfläche für AUR, Flatpak, Snap und AppImage.", pacman_packages=("bauh",)),
    InstallerSpec("cachy-update", KIND_UPDATE, "Update-Benachrichtigung von CachyOS im Infobereich der Taskleiste.",
                  pacman_packages=("cachy-update",)),
    InstallerSpec("arch-update", KIND_UPDATE, "Update-Benachrichtigung, Vorlage für cachy-update.", pacman_packages=("arch-update",)),
    InstallerSpec("Topgrade", KIND_UPDATE, "Aktualisiert mit einem Befehl alles: pacman, AUR, Flatpak, pipx, cargo, npm …",
                  binaries=("topgrade",)),
    InstallerSpec("Gear Lever", KIND_APPIMAGE, "Verwaltet AppImages und legt Startmenü-Einträge an.",
                  pacman_packages=("gearlever",), flatpak_ids=("it.mijorus.gearlever",)),
    InstallerSpec("AppImageLauncher", KIND_APPIMAGE, "Integriert AppImages beim ersten Start ins Startmenü.",
                  binaries=("AppImageLauncher",), pacman_packages=("appimagelauncher",)),
]


def detect(programs: list[Program]) -> list[InstallerStatus]:
    pacman_names = {p.name for p in programs if p.source in (Source.REPO, Source.AUR)}
    flatpak_ids = {p.name for p in programs if p.source is Source.FLATPAK}
    counts: dict[Source, int] = {}
    for p in programs:
        if p.explicit:
            counts[p.source] = counts.get(p.source, 0) + 1

    result = []
    for spec in SPECS:
        found = [b for b in spec.binaries if util.which(b)]
        found += [f"Paket {p}" for p in spec.pacman_packages if p in pacman_names]
        found += [f"Flatpak {f}" for f in spec.flatpak_ids if f in flatpak_ids]
        if spec.source is Source.BREW and find_brew():
            found.append("brew")
        present = bool(found)
        count = counts.get(spec.source, 0) if present and spec.source and spec.kind == KIND_PM else None
        result.append(InstallerStatus(spec, present, count, found))
    return result
