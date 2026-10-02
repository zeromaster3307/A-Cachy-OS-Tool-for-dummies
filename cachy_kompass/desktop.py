"""Startmenü-Einträge (``.desktop``-Dateien) lesen, zuordnen, anlegen und löschen.

Kurz erklärt: Jedes Programm im Startmenü hat eine kleine Textdatei mit der
Endung ``.desktop``. Sie liegt in einem „applications“-Ordner, z. B.
``/usr/share/applications`` (vom System) oder ``~/.local/share/applications``
(nur für dich). Darin steht u. a. der Name, das Symbol und der Startbefehl.
Eine Datei im Benutzerordner überdeckt eine gleichnamige Systemdatei.
"""

from __future__ import annotations

import locale
import os
import re
import shlex
from pathlib import Path

from cachy_kompass import util
from cachy_kompass.models import DesktopEntry, Program, Source

OUR_PREFIX = "cachy-kompass-"

# Startbefehle, die nur andere Programme aufrufen. Darüber ordnen wir nichts zu,
# sonst würde z. B. jeder Eintrag mit „sh -c …“ dem Paket bash zugerechnet.
GENERIC_LAUNCHERS = {
    "sh", "bash", "zsh", "fish", "dash", "env", "flatpak", "snap", "python", "python3",
    "java", "wine", "wine64", "xdg-open", "kioclient", "kioclient5", "kioclient6",
    "gtk-launch", "electron", "steam", "pkexec", "sudo", "gamemoderun", "systemd-run",
}

# Hauptkategorien laut freedesktop.org mit deutscher Beschriftung.
CATEGORIES = {
    "Utility": "Dienstprogramme",
    "AudioVideo": "Multimedia",
    "Development": "Entwicklung",
    "Education": "Bildung",
    "Game": "Spiele",
    "Graphics": "Grafik",
    "Network": "Internet",
    "Office": "Büro",
    "Science": "Wissenschaft",
    "Settings": "Einstellungen",
    "System": "System",
}


def user_applications_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(util.HOME / ".local" / "share")
    return Path(base) / "applications"


def applications_dirs() -> list[Path]:
    """Alle Ordner mit Startmenü-Einträgen, wichtigster zuerst."""
    data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    dirs = [user_applications_dir().parent] + [Path(p) for p in data_dirs.split(":") if p]
    dirs += [
        util.HOME / ".local" / "share" / "flatpak" / "exports" / "share",
        Path("/var/lib/flatpak/exports/share"),
        Path("/var/lib/snapd/desktop"),
    ]
    result: list[Path] = []
    for d in dirs:
        apps = d / "applications"
        if apps not in result:
            result.append(apps)
    return result


def _preferred_locales() -> list[str]:
    lang = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or ""
    if not lang:
        lang = locale.getlocale()[0] or ""
    lang = lang.split(".")[0].split("@")[0]
    result = []
    if lang and lang not in {"C", "POSIX"}:
        result.append(lang)
        if "_" in lang:
            result.append(lang.split("_")[0])
    return result


def localized(raw: dict[str, str], key: str) -> str:
    for loc in _preferred_locales():
        if f"{key}[{loc}]" in raw:
            return raw[f"{key}[{loc}]"]
    return raw.get(key, "")


def parse_desktop_text(text: str) -> dict[str, str]:
    """Liest die Gruppe ``[Desktop Entry]`` einer .desktop-Datei."""
    raw: dict[str, str] = {}
    in_main = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_main = line == "[Desktop Entry]"
            continue
        if in_main and "=" in line:
            key, value = line.split("=", 1)
            raw.setdefault(key.strip(), value.strip())
    return raw


def _bool(value: str) -> bool:
    return value.strip().lower() == "true"


def entry_from_raw(path: Path, file_id: str, raw: dict[str, str]) -> DesktopEntry:
    return DesktopEntry(
        path=path,
        file_id=file_id,
        name=localized(raw, "Name") or file_id.removesuffix(".desktop"),
        exec=raw.get("Exec", ""),
        icon=raw.get("Icon", ""),
        comment=localized(raw, "Comment") or localized(raw, "GenericName"),
        categories=[c for c in raw.get("Categories", "").split(";") if c],
        terminal=_bool(raw.get("Terminal", "false")),
        no_display=_bool(raw.get("NoDisplay", "false")),
        hidden=_bool(raw.get("Hidden", "false")),
        type=raw.get("Type", "Application"),
        raw=raw,
    )


def file_id_for(path: Path, apps_dir: Path) -> str:
    """Kennung eines Eintrags: Pfad relativ zum applications-Ordner, „/“ → „-“."""
    try:
        return str(path.relative_to(apps_dir)).replace("/", "-")
    except ValueError:
        return path.name


def file_id_from_path(path: str) -> str:
    """Kennung aus einem beliebigen Pfad, der „/applications/“ enthält."""
    _, sep, rest = path.partition("/applications/")
    return rest.replace("/", "-") if sep else Path(path).name


def load_entries(dirs: list[Path] | None = None) -> list[DesktopEntry]:
    """Alle wirksamen Einträge. Bei gleicher Kennung gewinnt der wichtigere Ordner."""
    entries: dict[str, DesktopEntry] = {}
    for apps_dir in dirs if dirs is not None else applications_dirs():
        if not apps_dir.is_dir():
            continue
        for path in sorted(apps_dir.rglob("*.desktop")):
            file_id = file_id_for(path, apps_dir)
            if file_id in entries:
                continue
            try:
                raw = parse_desktop_text(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            if raw:
                entries[file_id] = entry_from_raw(path, file_id, raw)
    return list(entries.values())


def exec_target(exec_line: str) -> str:
    """Das eigentlich gestartete Programm aus einer Exec-Zeile.

    ``env FOO=1 /usr/bin/firefox %u`` → ``/usr/bin/firefox``
    """
    try:
        tokens = shlex.split(exec_line)
    except ValueError:
        tokens = exec_line.split()
    for i, tok in enumerate(tokens):
        if tok == "env" and i == 0:
            continue
        if "=" in tok and not tok.startswith(("/", "%")) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok):
            continue  # Umgebungsvariable
        return tok
    return ""


def target_exists(target: str) -> bool:
    if not target:
        return False
    if target.startswith("/"):
        return os.path.exists(target)
    return util.which(target) is not None


def match_entries(programs: list[Program], entries: list[DesktopEntry]) -> list[DesktopEntry]:
    """Ordnet jedem Programm seine Startmenü-Einträge zu.

    Liefert die Einträge zurück, die keinem Programm zugeordnet werden konnten.

    Reihenfolge der Zuordnung:
      1. sichere Zuordnung (Datei gehört laut pacman zum Paket, Flatpak-ID, Snap-Name)
      2. über den Startbefehl (Exec), nur für noch nicht zugeordnete Einträge
    """
    by_id = {e.file_id: e for e in entries}
    assigned: set[str] = set()

    for prog in programs:
        prog.desktop_entries = []
        found: list[DesktopEntry] = []
        for owned in prog.owned_desktop_files:
            entry = by_id.get(file_id_from_path(owned))
            if entry:
                found.append(entry)
        if prog.source is Source.FLATPAK:
            found += [
                e for e in entries
                if e.raw.get("X-Flatpak") == prog.name or e.file_id.removesuffix(".desktop") == prog.name
            ]
        elif prog.source is Source.SNAP:
            found += [
                e for e in entries
                if e.raw.get("X-SnapInstanceName") == prog.name or e.file_id.startswith(f"{prog.name}_")
            ]
        for e in found:
            if e not in prog.desktop_entries:
                prog.desktop_entries.append(e)
                assigned.add(e.file_id)

    # Index der Programmdateien für die Zuordnung über den Startbefehl
    by_path: dict[str, list[Program]] = {}
    by_name: dict[str, list[Program]] = {}
    for prog in programs:
        for exe in prog.executables:
            by_path.setdefault(exe, []).append(prog)
            by_name.setdefault(Path(exe).name, []).append(prog)

    unmatched = []
    for e in entries:
        if e.file_id in assigned:
            continue
        target = exec_target(e.exec)
        if not target or Path(target).name in GENERIC_LAUNCHERS:
            unmatched.append(e)
            continue
        if target.startswith("/"):
            candidates = by_path.get(target) or by_path.get(os.path.realpath(target)) or []
        else:
            candidates = by_name.get(target, [])
        # Bei mehreren Treffern lieber explizit installierte Programme nehmen.
        candidates = sorted(candidates, key=lambda p: not p.explicit)[:1]
        for prog in candidates:
            prog.desktop_entries.append(e)
        if not candidates:
            unmatched.append(e)

    # Anzeigenamen verschönern: „org.gimp.GIMP“ → „GNU Image Manipulation Program“
    for prog in programs:
        visible = [e for e in prog.desktop_entries if e.visible]
        if visible and prog.display_name == prog.name and prog.source is not Source.FLATPAK:
            prog.display_name = visible[0].name
    return unmatched


# --- Einträge anlegen / löschen ----------------------------------------------


def quote_exec_arg(arg: str) -> str:
    """Setzt ein Argument nach den Regeln der Desktop-Spezifikation in Anführungszeichen."""
    if arg and not re.search(r"[\s\"'\\><~|&;$*?#()`]", arg):
        return arg
    escaped = re.sub(r'(["`$\\])', r"\\\1", arg)
    return f'"{escaped}"'


def suggest_exec(prog: Program) -> str:
    """Schlägt einen Startbefehl für ein Programm vor."""
    if prog.source is Source.FLATPAK:
        return f"flatpak run {prog.name}"
    if prog.source is Source.SNAP:
        return f"snap run {prog.name}"
    exes = prog.executables
    if not exes:
        return prog.name
    preferred = [e for e in exes if Path(e).name.lower() == prog.name.lower()]
    return quote_exec_arg((preferred or exes)[0])


def suggest_icon(prog: Program) -> str:
    if prog.source is Source.FLATPAK:
        return prog.name
    return prog.name.lower()


def _clean(value: str) -> str:
    """Zeilenumbrüche würden die Datei kaputt machen."""
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "programm"


def build_desktop_text(
    name: str,
    exec_line: str,
    icon: str = "",
    comment: str = "",
    categories: list[str] | None = None,
    terminal: bool = False,
) -> str:
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        "Version=1.5",
        f"Name={_clean(name)}",
    ]
    if comment:
        lines.append(f"Comment={_clean(comment)}")
    lines.append(f"Exec={_clean(exec_line)}")
    if icon:
        lines.append(f"Icon={_clean(icon)}")
    lines.append(f"Terminal={'true' if terminal else 'false'}")
    cats = [c for c in (categories or []) if c]
    if cats:
        lines.append("Categories=" + ";".join(cats) + ";")
    lines.append("X-Cachy-Kompass=true")
    return "\n".join(lines) + "\n"


def create_entry(
    name: str,
    exec_line: str,
    icon: str = "",
    comment: str = "",
    categories: list[str] | None = None,
    terminal: bool = False,
    target_dir: Path | None = None,
) -> Path:
    """Legt einen neuen Startmenü-Eintrag im Benutzerordner an und gibt den Pfad zurück."""
    if not name.strip() or not exec_line.strip():
        raise ValueError("Name und Startbefehl dürfen nicht leer sein.")
    target_dir = target_dir or user_applications_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    base = f"{OUR_PREFIX}{_slug(name)}"
    path = target_dir / f"{base}.desktop"
    counter = 2
    while path.exists():
        path = target_dir / f"{base}-{counter}.desktop"
        counter += 1
    path.write_text(build_desktop_text(name, exec_line, icon, comment, categories, terminal), encoding="utf-8")
    path.chmod(0o644)
    refresh_menu_cache(target_dir)
    return path


def remove_entry(entry: DesktopEntry) -> None:
    """Löscht einen Eintrag – aber nur, wenn wir ihn selbst angelegt haben."""
    if not entry.created_by_us:
        raise PermissionError("Dieser Eintrag wurde nicht vom Software-Kompass angelegt und wird nicht gelöscht.")
    entry.path.unlink()
    refresh_menu_cache(entry.path.parent)


def refresh_menu_cache(apps_dir: Path) -> None:
    """Bittet die Desktop-Umgebung, das Startmenü neu einzulesen (falls möglich)."""
    if util.which("update-desktop-database"):
        util.run(["update-desktop-database", str(apps_dir)], timeout=30)
    for tool in ("kbuildsycoca6", "kbuildsycoca5"):  # KDE Plasma
        if util.which(tool):
            util.run([tool], timeout=60)
            break


def validate(path: Path) -> str:
    """Prüft eine .desktop-Datei mit ``desktop-file-validate`` (falls installiert)."""
    if not util.which("desktop-file-validate"):
        return ""
    out = util.run(["desktop-file-validate", str(path)], ok_codes=(0, 1))
    return (out or "").strip()
