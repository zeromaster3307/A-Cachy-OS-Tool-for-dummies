"""Datenmodelle: Was wissen wir über ein installiertes Programm?

Alle Texte, die später in der Oberfläche landen, stehen bewusst hier zentral,
damit man sie leicht anpassen oder übersetzen kann.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Source(Enum):
    """Über welchen Weg ein Programm auf das System gekommen ist."""

    REPO = "repo"
    AUR = "aur"
    FLATPAK = "flatpak"
    SNAP = "snap"
    APPIMAGE = "appimage"
    PIPX = "pipx"
    UV = "uv"
    CARGO = "cargo"
    NPM = "npm"
    BREW = "brew"
    MANUAL = "manual"


class AutoUpdate(Enum):
    """Wird das Programm beim normalen CachyOS-Systemupdate mit aktualisiert?"""

    YES = "ja"
    PARTIAL = "teilweise"
    NO = "nein"


class UpdateStatus(Enum):
    """Ergebnis der Prüfung, ob eine neuere Version verfügbar ist."""

    NOT_CHECKED = "nicht geprüft"
    CURRENT = "aktuell"
    OUTDATED = "Update verfügbar"
    UNKNOWN = "unbekannt"
    NOT_CHECKABLE = "nicht prüfbar"


class MenuStatus(Enum):
    """Ist das Programm über das Startmenü erreichbar?"""

    VISIBLE = "ja"
    HIDDEN = "versteckt"
    NONE = "nein"


@dataclass(frozen=True)
class SourceInfo:
    """Allgemeinverständliche Beschreibung einer Installationsquelle."""

    label: str
    how_installed: str
    auto_update: AutoUpdate
    update_hint: str
    uninstall_template: str
    # Kommandozeilenprogramme brauchen beim Startmenü-Eintrag ein Terminal.
    cli_by_default: bool = False


SOURCE_INFO: dict[Source, SourceInfo] = {
    Source.REPO: SourceInfo(
        label="Offizielles Repo",
        how_installed=(
            "Installiert mit der Paketverwaltung pacman aus einer offiziellen "
            "Paketquelle (CachyOS- oder Arch-Linux-Repo), z. B. mit "
            "„sudo pacman -S …“, dem CachyOS Package Installer oder Octopi."
        ),
        auto_update=AutoUpdate.YES,
        update_hint=(
            "Wird bei jedem normalen Systemupdate automatisch mit aktualisiert "
            "(„sudo pacman -Syu“, „paru“ oder die CachyOS-Update-Benachrichtigung)."
        ),
        uninstall_template="sudo pacman -Rns {name}",
    ),
    Source.AUR: SourceInfo(
        label="AUR",
        how_installed=(
            "Aus dem Arch User Repository (AUR) gebaut, meist mit einem "
            "AUR-Helfer wie paru oder yay. Das AUR ist eine Sammlung von "
            "Bauanleitungen aus der Community und nicht offiziell geprüft. "
            "Pakete, die nicht mehr im AUR stehen, wurden evtl. von Hand gebaut "
            "oder sind aus einem offiziellen Repo entfernt worden."
        ),
        auto_update=AutoUpdate.PARTIAL,
        update_hint=(
            "Wird nur aktualisiert, wenn du dein System mit einem AUR-Helfer "
            "aktualisierst (z. B. „paru“ oder „yay“). Ein reines "
            "„sudo pacman -Syu“ aktualisiert AUR-Programme NICHT."
        ),
        uninstall_template="sudo pacman -Rns {name}",
    ),
    Source.FLATPAK: SourceInfo(
        label="Flatpak",
        how_installed=(
            "Als Flatpak installiert, meist aus Flathub – z. B. über Discover, "
            "GNOME Software, die Flathub-Webseite oder „flatpak install …“. "
            "Flatpaks laufen abgeschottet vom restlichen System."
        ),
        auto_update=AutoUpdate.PARTIAL,
        update_hint=(
            "Wird NICHT von pacman aktualisiert. Aktualisiere mit "
            "„flatpak update“ oder über Discover / GNOME Software, die das "
            "je nach Einstellung auch automatisch erledigen."
        ),
        uninstall_template="flatpak uninstall {name}",
    ),
    Source.SNAP: SourceInfo(
        label="Snap",
        how_installed=(
            "Als Snap-Paket installiert („sudo snap install …“). Unter "
            "CachyOS ist Snap nicht standardmäßig dabei und wurde vermutlich "
            "nach einer Anleitung nachinstalliert."
        ),
        auto_update=AutoUpdate.YES,
        update_hint=(
            "Snap aktualisiert sich selbstständig im Hintergrund "
            "(mehrmals täglich), unabhängig vom CachyOS-Systemupdate."
        ),
        uninstall_template="sudo snap remove {name}",
    ),
    Source.APPIMAGE: SourceInfo(
        label="AppImage",
        how_installed=(
            "Eine AppImage-Datei, die von einer Webseite heruntergeladen wurde. "
            "Sie wird nicht installiert, sondern direkt gestartet. Werkzeuge "
            "wie Gear Lever oder AppImageLauncher legen dafür evtl. "
            "Startmenü-Einträge an."
        ),
        auto_update=AutoUpdate.NO,
        update_hint=(
            "Wird NICHT automatisch aktualisiert. Lade die neue Version selbst "
            "herunter oder nutze ein Werkzeug wie Gear Lever."
        ),
        uninstall_template="rm {qpath}",
    ),
    Source.PIPX: SourceInfo(
        label="pipx (Python)",
        how_installed=(
            "Ein Python-Programm, installiert mit „pipx install …“ in eine "
            "eigene, abgeschottete Umgebung im Benutzerordner."
        ),
        auto_update=AutoUpdate.NO,
        update_hint="Wird NICHT automatisch aktualisiert. Aktualisieren mit „pipx upgrade-all“.",
        uninstall_template="pipx uninstall {name}",
        cli_by_default=True,
    ),
    Source.UV: SourceInfo(
        label="uv tool (Python)",
        how_installed=(
            "Ein Python-Programm, installiert mit „uv tool install …“ "
            "(ähnlich wie pipx, nur schneller)."
        ),
        auto_update=AutoUpdate.NO,
        update_hint="Wird NICHT automatisch aktualisiert. Aktualisieren mit „uv tool upgrade --all“.",
        uninstall_template="uv tool uninstall {name}",
        cli_by_default=True,
    ),
    Source.CARGO: SourceInfo(
        label="cargo (Rust)",
        how_installed=(
            "Ein Rust-Programm, aus dem Quellcode gebaut mit „cargo install …“. "
            "Die Programmdatei liegt in ~/.cargo/bin."
        ),
        auto_update=AutoUpdate.NO,
        update_hint=(
            "Wird NICHT automatisch aktualisiert. Erneut „cargo install {name}“ "
            "ausführen oder das Zusatzwerkzeug cargo-update nutzen "
            "(„cargo install-update -a“)."
        ),
        uninstall_template="cargo uninstall {name}",
        cli_by_default=True,
    ),
    Source.NPM: SourceInfo(
        label="npm (Node.js)",
        how_installed="Ein Node.js-Programm, global installiert mit „npm install -g …“.",
        auto_update=AutoUpdate.NO,
        update_hint="Wird NICHT automatisch aktualisiert. Aktualisieren mit „npm update -g“.",
        uninstall_template="npm uninstall -g {name}",
        cli_by_default=True,
    ),
    Source.BREW: SourceInfo(
        label="Homebrew",
        how_installed=(
            "Installiert mit Homebrew („brew install …“). Homebrew kommt "
            "eigentlich von macOS und wurde vermutlich nach einer Anleitung "
            "nachinstalliert."
        ),
        auto_update=AutoUpdate.NO,
        update_hint="Wird NICHT vom Systemupdate erfasst. Aktualisieren mit „brew upgrade“.",
        uninstall_template="brew uninstall {name}",
        cli_by_default=True,
    ),
    Source.MANUAL: SourceInfo(
        label="Manuell",
        how_installed=(
            "Von Hand ins System kopiert (z. B. ein entpacktes Archiv in /opt "
            "oder eine Programmdatei in ~/.local/bin oder /usr/local/bin). "
            "Keine Paketverwaltung weiß davon."
        ),
        auto_update=AutoUpdate.NO,
        update_hint=(
            "Wird NICHT automatisch aktualisiert. Updates musst du selbst "
            "beim Hersteller herunterladen."
        ),
        uninstall_template="{rm} {qpath}",
    ),
}


@dataclass
class DesktopEntry:
    """Ein Startmenü-Eintrag (eine ``.desktop``-Datei)."""

    path: Path
    file_id: str
    name: str
    exec: str = ""
    icon: str = ""
    comment: str = ""
    categories: list[str] = field(default_factory=list)
    terminal: bool = False
    no_display: bool = False
    hidden: bool = False
    type: str = "Application"
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def visible(self) -> bool:
        """Erscheint der Eintrag tatsächlich im Startmenü?"""
        return self.type == "Application" and not self.no_display and not self.hidden

    @property
    def created_by_us(self) -> bool:
        """Wurde der Eintrag von diesem Programm angelegt (und darf gelöscht werden)?"""
        return self.raw.get("X-Cachy-Kompass", "").lower() == "true"


@dataclass
class UpdateResult:
    """Ergebnis einer Update-Prüfung für ein einzelnes Programm."""

    status: UpdateStatus
    latest: str = ""
    note: str = ""


@dataclass
class Program:
    """Ein installiertes Programm – egal aus welcher Quelle."""

    name: str
    version: str
    source: Source
    display_name: str = ""
    description: str = ""
    # Woher genau? z. B. Repo-Name „cachyos-v3“, Flatpak-Remote „flathub“
    origin: str = ""
    # False = nur als Abhängigkeit/Bibliothek installiert
    explicit: bool = True
    # Programmdateien (absolute Pfade), die zu diesem Programm gehören
    executables: list[str] = field(default_factory=list)
    # .desktop-Dateien, die sicher zu diesem Programm gehören (z. B. laut pacman)
    owned_desktop_files: list[str] = field(default_factory=list)
    install_path: str = ""
    url: str = ""
    install_date: str = ""
    # Bei Flatpak: "user" oder "system"
    installation: str = ""
    # Eigener Deinstallationsbefehl, falls die Vorlage der Quelle nicht passt
    uninstall_override: str = ""
    desktop_entries: list[DesktopEntry] = field(default_factory=list)
    update: UpdateResult = field(default_factory=lambda: UpdateResult(UpdateStatus.NOT_CHECKED))

    def __post_init__(self) -> None:
        if not self.display_name:
            self.display_name = self.name

    @property
    def key(self) -> str:
        """Eindeutiger Schlüssel über alle Quellen hinweg."""
        return f"{self.source.value}:{self.name}"

    @property
    def info(self) -> SourceInfo:
        return SOURCE_INFO[self.source]

    @property
    def menu_status(self) -> MenuStatus:
        if any(e.visible for e in self.desktop_entries):
            return MenuStatus.VISIBLE
        if self.desktop_entries:
            return MenuStatus.HIDDEN
        return MenuStatus.NONE

    def uninstall_command(self) -> str:
        if self.uninstall_override:
            return self.uninstall_override
        template = self.info.uninstall_template
        if self.source is Source.FLATPAK and self.installation == "user":
            template = "flatpak uninstall --user {name}"
        path = self.install_path or "?"
        # Außerhalb des Benutzerordners braucht man Administratorrechte;
        # Ordner müssen mitsamt Inhalt („-r“) gelöscht werden.
        in_home = path.startswith(str(Path.home()) + "/")
        rm = ("rm -r" if Path(path).is_dir() else "rm") if in_home else ("sudo rm -r" if Path(path).is_dir() else "sudo rm")
        return template.format(name=self.name, qpath=shlex.quote(path), rm=rm)

    def search_text(self) -> str:
        """Alles, wonach man suchen können sollte – in Kleinbuchstaben.

        Neben Name und Beschreibung auch die Namen der Startmenü-Einträge
        (z. B. „Claude Code“ für das Programm „claude“), Herkunft und Befehle.
        """
        parts = [self.display_name, self.name, self.description, self.origin, self.info.label]
        parts += [f"{e.name} {e.comment}" for e in self.desktop_entries]
        parts += [Path(x).name for x in self.executables]
        return " ".join(parts).lower()

    def update_hint(self) -> str:
        return self.info.update_hint.format(name=self.name)
