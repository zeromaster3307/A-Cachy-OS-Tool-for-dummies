"""Welche Paketverwaltungen, App-Stores und Update-Werkzeuge sind vorhanden –
und welche davon sind unter CachyOS empfehlenswert?

Viele Anleitungen im Netz sagen „installiere erst X, dann Y“. Diese Übersicht
zeigt, welche dieser Werkzeuge auf dem System gelandet sind, und bewertet sie.

Grundsätze fürs Installieren:
  * Nur Werkzeuge mit Einstufung „empfohlen“ oder „bei Bedarf“ bekommen einen
    Installieren-Knopf – „nicht empfohlen“ nie.
  * Installiert wird nur aus den offiziellen Paketquellen (CachyOS/Arch), die
    Verfügbarkeit wird vorher mit ``pacman -Si`` geprüft. Einzige Ausnahme:
    Flatpak-Apps von Flathub, wenn Flatpak schon vorhanden ist.
  * Kein AUR, keine Skripte aus dem Internet.
  * Der Befehl läuft sichtbar in einem Terminal (siehe ``terminal.py``),
    der Software-Kompass selbst bekommt nie Administratorrechte.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from cachy_kompass import util
from cachy_kompass.i18n import _
from cachy_kompass.models import Program, Source
from cachy_kompass.sources.devtools import find_brew


class Rating(Enum):
    BASE = _("Grundausstattung")
    RECOMMENDED = _("✔ empfohlen")
    OPTIONAL = _("◐ bei Bedarf")
    DISCOURAGED = _("✘ nicht empfohlen")


@dataclass(frozen=True)
class InstallerSpec:
    name: str
    kind: str
    description: str
    rating: Rating
    #: Warum diese Einstufung? (für Laien formuliert)
    reason: str
    binaries: tuple[str, ...] = ()
    pacman_packages: tuple[str, ...] = ()
    flatpak_ids: tuple[str, ...] = ()
    source: Source | None = None  # zugehörige Quelle (für die Anzahl der Programme)
    #: Pakete aus den offiziellen Repos, die zum Installieren nötig sind
    install_packages: tuple[str, ...] = ()
    #: Ersatzweise als Flatpak von Flathub (nur wenn Flatpak vorhanden ist)
    install_flatpak: str = ""
    #: Hinweis, der nach der Installation wichtig ist
    after_install: str = ""


@dataclass
class InstallerStatus:
    spec: InstallerSpec
    present: bool
    program_count: int | None = None
    found_via: list[str] = field(default_factory=list)
    #: Befehl zum Installieren – ``None``, wenn wir keinen anbieten
    install_command: list[str] | None = None
    #: Warum es (k)einen Installieren-Knopf gibt
    install_note: str = ""

    @property
    def uninstall_command(self) -> str:
        pkgs = [p for p in self.spec.install_packages or self.spec.pacman_packages if p]
        return f"sudo pacman -Rns {' '.join(pkgs)}" if pkgs else ""


KIND_PM = _("Paketverwaltung")
KIND_GUI = _("Grafischer App-Store")
KIND_UPDATE = _("Update-Werkzeug")
KIND_APPIMAGE = _("AppImage-Helfer")

SPECS: list[InstallerSpec] = [
    InstallerSpec("pacman", KIND_PM, _("Die Paketverwaltung von Arch Linux und CachyOS. Immer vorhanden."),
                  Rating.BASE, _("Das Herzstück des Systems."), binaries=("pacman",), source=Source.REPO),
    InstallerSpec("paru", KIND_PM, _("AUR-Helfer, bei CachyOS vorinstalliert. Installiert Programme aus dem AUR und aktualisiert Repo- und AUR-Pakete gemeinsam."),
                  Rating.RECOMMENDED, _("Der AUR-Helfer, den CachyOS selbst mitbringt. Einer reicht."),
                  binaries=("paru",), source=Source.AUR, install_packages=("paru",)),
    InstallerSpec("yay", KIND_PM, _("Weit verbreiteter AUR-Helfer, wird in vielen Anleitungen nachinstalliert."),
                  Rating.DISCOURAGED, _("Macht dasselbe wie paru, das bei CachyOS schon dabei ist. Zwei AUR-Helfer stiften nur Verwirrung. "
                     "Wenn eine Anleitung „yay -S …“ sagt, nimm einfach „paru -S …“."),
                  binaries=("yay",), source=Source.AUR),
    InstallerSpec("pikaur / trizen", KIND_PM, _("Weitere AUR-Helfer."),
                  Rating.DISCOURAGED, _("Wie bei yay: paru ist schon da und reicht völlig."),
                  binaries=("pikaur", "trizen"), source=Source.AUR),
    InstallerSpec("Flatpak", KIND_PM, _("Abgeschottete Apps aus Flathub. Unabhängig von pacman."),
                  Rating.RECOMMENDED, _("Riesige Auswahl an Programmen (Flathub), sauber vom System getrennt und in Discover eingebunden. "
                     "Gute Ergänzung, wenn ein Programm nicht in den Repos ist – besser als das AUR für Einsteiger."),
                  binaries=("flatpak",), source=Source.FLATPAK, install_packages=("flatpak",),
                  after_install=_("Einmal ab- und wieder anmelden, damit Flatpak-Programme im Startmenü erscheinen. "
                                "Flathub ist unter Arch/CachyOS automatisch eingerichtet.")),
    InstallerSpec("Snap (snapd)", KIND_PM, _("Paketsystem von Ubuntu. Unter CachyOS nicht vorgesehen, meist aus dem AUR nachinstalliert."),
                  Rating.DISCOURAGED, _("Nur über das AUR erhältlich und unter Arch schlecht eingebunden. Fast alles, was es als Snap gibt, "
                     "gibt es auch als Flatpak oder in den Repos."),
                  binaries=("snap",), source=Source.SNAP),
    InstallerSpec("pipx", KIND_PM, _("Installiert Python-Programme in eigene Umgebungen."),
                  Rating.OPTIONAL, _("Der saubere Weg für Python-Programme, die es nicht in den Repos gibt (statt „pip install“)."),
                  binaries=("pipx",), source=Source.PIPX, install_packages=("python-pipx",)),
    InstallerSpec("uv", KIND_PM, _("Schneller Python-Paketmanager, kann mit „uv tool“ Programme installieren."),
                  Rating.OPTIONAL, _("Moderne, schnelle Alternative zu pipx. Eins von beiden reicht."),
                  binaries=("uv",), source=Source.UV, install_packages=("uv",)),
    InstallerSpec("pip (Python)", KIND_PM, _("Python-Paketinstaller."),
                  Rating.DISCOURAGED, _("„pip install“ am System vorbei kann Python-Programme des Systems beschädigen und wird unter "
                     "Arch/CachyOS deshalb blockiert. Für Programme: pipx oder uv nehmen."),
                  binaries=("pip", "pip3")),
    InstallerSpec("cargo (Rust)", KIND_PM, _("Baut Rust-Programme aus dem Quellcode."),
                  Rating.OPTIONAL, _("Nur nötig, wenn du Rust-Programme selbst bauen willst. Die meisten gibt es fertig in den Repos."),
                  binaries=("cargo",), source=Source.CARGO, install_packages=("rust",)),
    InstallerSpec("npm (Node.js)", KIND_PM, _("Paketverwaltung für JavaScript/Node.js."),
                  Rating.OPTIONAL, _("Nur nötig, wenn eine Anleitung ein Programm per „npm install -g“ verlangt."),
                  binaries=("npm",), source=Source.NPM, install_packages=("npm",)),
    InstallerSpec("Homebrew", KIND_PM, _("Paketverwaltung aus der macOS-Welt, gibt es auch für Linux."),
                  Rating.DISCOURAGED, _("Wird per Skript aus dem Internet installiert und legt eine zweite, komplette Software-Welt neben "
                     "pacman an. Unter CachyOS gibt es fast alles in den Repos oder im AUR."),
                  source=Source.BREW),
    InstallerSpec("Nix", KIND_PM, _("Eigenständige Paketverwaltung mit eigenem Paketbestand. (Programme daraus werden noch nicht einzeln aufgelistet.)"),
                  Rating.DISCOURAGED, _("Mächtig, aber ein eigenes Universum mit eigener Denkweise – nichts für Einsteiger."),
                  binaries=("nix", "nix-env")),
    InstallerSpec("Distrobox", KIND_PM, _("Startet andere Linux-Systeme (z. B. Ubuntu) im Container. Programme darin werden hier nicht erfasst."),
                  Rating.OPTIONAL, _("Praktisch, wenn ein Programm nur für Ubuntu/Fedora angeboten wird. Braucht zusätzlich Podman."),
                  binaries=("distrobox",), install_packages=("distrobox", "podman")),
    InstallerSpec("go", KIND_PM, _("Programmiersprache Go; „go install“ legt Programme in ~/go/bin ab."),
                  Rating.OPTIONAL, _("Nur für Entwickler bzw. wenn eine Anleitung „go install“ verlangt."),
                  binaries=("go",), install_packages=("go",)),
    InstallerSpec("CachyOS Package Installer", KIND_GUI, _("Grafisches Programm von CachyOS zum Installieren beliebter Software aus den Repos."),
                  Rating.RECOMMENDED, _("Das offizielle, einsteigerfreundliche Installationsprogramm von CachyOS."),
                  pacman_packages=("cachyos-packageinstaller",), source=Source.REPO,
                  install_packages=("cachyos-packageinstaller",)),
    InstallerSpec("CachyOS Hello", KIND_GUI, _("Willkommens-App von CachyOS mit Abkürzungen zu Software und Einstellungen."),
                  Rating.RECOMMENDED, _("Offizielles CachyOS-Werkzeug mit nützlichen Abkürzungen."),
                  pacman_packages=("cachyos-hello",), install_packages=("cachyos-hello",)),
    InstallerSpec("Octopi", KIND_GUI, _("Grafische Oberfläche für pacman (und AUR)."),
                  Rating.OPTIONAL, _("Für alle, die Pakete lieber per Maus als im Terminal verwalten."),
                  pacman_packages=("octopi",), install_packages=("octopi",)),
    InstallerSpec("Pamac", KIND_GUI, _("App-Store von Manjaro, oft aus dem AUR nachinstalliert. Kann Repo, AUR und Flatpak."),
                  Rating.DISCOURAGED, _("Für Manjaro gebaut und unter CachyOS nur aus dem AUR zu bekommen. "
                     "Besser: CachyOS Package Installer, Octopi oder Discover."),
                  pacman_packages=("pamac-aur", "pamac-all", "pamac-gtk", "pamac-gtk3", "pamac-cli")),
    InstallerSpec("Discover", KIND_GUI, _("App-Store von KDE Plasma. Kann Repo-Pakete und Flatpaks installieren und aktualisieren."),
                  Rating.OPTIONAL, _("Bequemer App-Store unter KDE, besonders für Flatpaks."),
                  pacman_packages=("discover",), install_packages=("discover",)),
    InstallerSpec("GNOME Software", KIND_GUI, _("App-Store von GNOME. Kann Repo-Pakete und Flatpaks installieren."),
                  Rating.OPTIONAL, _("Nur unter dem GNOME-Desktop sinnvoll – unter KDE ist Discover die passende Wahl."),
                  pacman_packages=("gnome-software",), install_packages=("gnome-software",)),
    InstallerSpec("Bauh", KIND_GUI, _("Grafische Oberfläche für AUR, Flatpak, Snap und AppImage."),
                  Rating.DISCOURAGED, _("Nur aus dem AUR und kaum noch gepflegt. Besser: Discover für Flatpaks, Octopi für Pakete."),
                  pacman_packages=("bauh",)),
    InstallerSpec("cachy-update", KIND_UPDATE, _("Update-Benachrichtigung von CachyOS im Infobereich der Taskleiste."),
                  Rating.RECOMMENDED, _("Erinnert dich an Updates und spielt sie mit einem Klick ein."),
                  pacman_packages=("cachy-update",), install_packages=("cachy-update",)),
    InstallerSpec("arch-update", KIND_UPDATE, _("Update-Benachrichtigung, Vorlage für cachy-update."),
                  Rating.DISCOURAGED, _("cachy-update ist die an CachyOS angepasste Variante – beides gleichzeitig ist doppelt."),
                  pacman_packages=("arch-update",)),
    InstallerSpec("Topgrade", KIND_UPDATE, _("Aktualisiert mit einem Befehl alles: pacman, AUR, Flatpak, pipx, cargo, npm …"),
                  Rating.OPTIONAL, _("Praktisch, wenn du viele verschiedene Paketverwaltungen nutzt."),
                  binaries=("topgrade",), install_packages=("topgrade",)),
    InstallerSpec("Gear Lever", KIND_APPIMAGE, _("Verwaltet AppImages und legt Startmenü-Einträge an."),
                  Rating.OPTIONAL, _("Empfehlenswert, wenn du AppImages nutzt: hält sie an einem Ort, legt Menüeinträge an und kann sie aktualisieren."),
                  pacman_packages=("gearlever",), flatpak_ids=("it.mijorus.gearlever",),
                  install_packages=("gearlever",), install_flatpak="it.mijorus.gearlever"),
    InstallerSpec("AppImageLauncher", KIND_APPIMAGE, _("Integriert AppImages beim ersten Start ins Startmenü."),
                  Rating.DISCOURAGED, _("Nur aus dem AUR und kaum noch weiterentwickelt. Gear Lever ist die modernere Alternative."),
                  binaries=("AppImageLauncher",), pacman_packages=("appimagelauncher",)),
]


def parse_si_names(text: str) -> set[str]:
    """``pacman -Si a b c`` → Namen der Pakete, die in einem Repo gefunden wurden."""
    names = set()
    for line in text.splitlines():
        if line.startswith("Name") and ":" in line:
            names.add(line.split(":", 1)[1].strip())
    return names


def repo_available(packages: set[str]) -> set[str]:
    """Welche der Pakete gibt es in den eingerichteten offiziellen Repos?"""
    if not packages or not util.which("pacman"):
        return set()
    # Code 1, wenn mindestens ein Paket fehlt – die übrigen werden trotzdem gezeigt.
    return parse_si_names(util.run(["pacman", "-Si", *sorted(packages)], timeout=60, ok_codes=(0, 1)) or "")


def plan_install(spec: InstallerSpec, available: set[str], flatpak_present: bool) -> tuple[list[str] | None, str]:
    """Entscheidet, ob und wie ein Werkzeug installiert werden darf."""
    if spec.rating is Rating.DISCOURAGED:
        return None, _("Wird bewusst nicht zur Installation angeboten (siehe Begründung).")
    if spec.rating is Rating.BASE:
        return None, ""
    if spec.install_packages and all(p in available for p in spec.install_packages):
        return ["sudo", "pacman", "-S", "--needed", *spec.install_packages], _("Aus den offiziellen Paketquellen.")
    if spec.install_flatpak and flatpak_present:
        return ["flatpak", "install", "flathub", spec.install_flatpak], _("Als Flatpak von Flathub.")
    if spec.install_packages:
        return None, _(
            "Nicht in deinen offiziellen Paketquellen gefunden – wird deshalb nicht angeboten "
            "(der Software-Kompass installiert nichts aus dem AUR oder aus dem Internet)."
        )
    return None, ""


def detect(programs: list[Program]) -> list[InstallerStatus]:
    pacman_names = {p.name for p in programs if p.source in (Source.REPO, Source.AUR)}
    flatpak_ids = {p.name for p in programs if p.source is Source.FLATPAK}
    counts: dict[Source, int] = {}
    for p in programs:
        if p.explicit:
            counts[p.source] = counts.get(p.source, 0) + 1

    statuses = []
    for spec in SPECS:
        found = [b for b in spec.binaries if util.which(b)]
        found += [_("Paket {name}").format(name=p) for p in spec.pacman_packages if p in pacman_names]
        found += [f"Flatpak {f}" for f in spec.flatpak_ids if f in flatpak_ids]
        if spec.source is Source.BREW and find_brew():
            found.append("brew")
        present = bool(found)
        count = counts.get(spec.source, 0) if present and spec.source and spec.kind == KIND_PM else None
        statuses.append(InstallerStatus(spec, present, count, found))

    # Nur für fehlende Werkzeuge nachsehen, ob die Repos sie anbieten – ein einziger Aufruf.
    wanted = {pkg for s in statuses if not s.present and s.spec.rating in (Rating.RECOMMENDED, Rating.OPTIONAL) for pkg in s.spec.install_packages}
    available = repo_available(wanted)
    flatpak_present = util.which("flatpak") is not None
    for s in statuses:
        if not s.present:
            s.install_command, s.install_note = plan_install(s.spec, available, flatpak_present)
    return statuses
