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
import shutil
from pathlib import Path

from cachy_kompass import util
from cachy_kompass.models import DesktopEntry, Program, Source

OUR_PREFIX = "cachy-kompass-"

# Startbefehle, die nur andere Programme aufrufen. Darüber ordnen wir nichts zu,
# sonst würde z. B. jeder Eintrag mit „sh -c …“ dem Paket bash zugerechnet.
#
# Zwei Arten:
#   * Vorschalt-Programme starten das nächste Wort als Programm
#     („gamemoderun foo“, „sudo foo“).
#   * Programm-Starter bekommen danach nur ein Argument – kein Programm
#     („wine start …“, „steam steam://…“, „flatpak run org.x“, „python3 skript.py“).
WRAPPERS = {
    "env", "nohup", "pkexec", "sudo", "gamemoderun", "systemd-run", "prime-run", "mangohud", "gamescope",
}
HANDLERS = {
    "flatpak", "snap", "python", "python3", "java", "wine", "wine64", "xdg-open", "kioclient",
    "kioclient5", "kioclient6", "gtk-launch", "electron", "steam", "node", "mono", "dotnet",
}
GENERIC_LAUNCHERS = WRAPPERS | HANDLERS | {"sh", "bash", "zsh", "fish", "dash"}

# Shell-Befehle, die kein eigenes Programm sind (für „sh -c '…'“-Einträge)
_SHELL_BUILTINS = {
    "cd", "exec", "export", "source", ".", "if", "then", "else", "fi", "for", "do", "done", "while",
    "case", "esac", "exit", "set", "unset", "[", "[[", "test", "true", "false", "echo", "printf",
    "read", "eval", "trap", "wait", "sleep", "command", "builtin",
}

# Terminalprogramme: Ein Eintrag wie „konsole -e claude“ gehört zu claude,
# nicht zu Konsole.
TERMINALS = {
    "konsole", "yakuake", "gnome-terminal", "kgx", "ptyxis", "kitty", "alacritty", "foot",
    "footclient", "wezterm", "ghostty", "xterm", "uxterm", "urxvt", "tilix", "terminator",
    "xfce4-terminal", "mate-terminal", "lxterminal", "qterminal", "xdg-terminal-exec", "st",
    "warp-terminal", "cool-retro-term", "rio", "contour",
}
# Optionen, nach denen bei Terminals der eigentliche Befehl folgt
_TERMINAL_COMMAND_FLAGS = {"-e", "-x", "--", "--command", "--exec", "-c"}
_SHELLS = {"sh", "bash", "zsh", "fish", "dash"}

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


# Bildformate, die alle Desktop-Umgebungen direkt als Symbol verstehen
ICON_FORMATS = (".svg", ".png", ".xpm")


def _data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or str(util.HOME / ".local" / "share"))


def user_applications_dir() -> Path:
    return _data_home() / "applications"


def user_icon_dir() -> Path:
    """Hier legen wir Kopien der ausgewählten Symbolbilder ab."""
    return _data_home() / "icons" / "cachy-kompass"


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


def _split(exec_line: str) -> list[str]:
    try:
        return shlex.split(exec_line)
    except ValueError:
        return exec_line.split()


def exec_candidates(exec_line: str) -> list[str]:
    """Alle Programme, die eine Exec-Zeile der Reihe nach aufruft.

    Durchschaut Umgebungsvariablen, Terminals und Shells:
    ``konsole -e claude``        → ``["konsole", "claude"]``
    ``sh -c "cd ~; exec foo -x"`` → ``["sh", "cd", "exec", "foo"]`` (Shell-Befehl wird zerlegt)
    """
    tokens = [t for t in _split(exec_line) if t and not t.startswith("%")]
    result: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        name = Path(tok).name
        if tok == "env" or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok) or tok.startswith("-"):
            i += 1
            continue
        result.append(tok)
        rest = tokens[i + 1 :]
        if name in TERMINALS:
            # Bei „-e“, „--“ usw. direkt zum eigentlichen Befehl springen
            marker = next((j for j, r in enumerate(rest) if r in _TERMINAL_COMMAND_FLAGS), None)
            i = i + 1 + (marker + 1 if marker is not None else 0)
            continue
        if name in _SHELLS and "-c" in rest:
            inner = rest[rest.index("-c") + 1] if rest.index("-c") + 1 < len(rest) else ""
            for part in re.split(r"[;&|]+", inner):
                result.extend(c for c in exec_candidates(part) if c not in _SHELL_BUILTINS)
            break
        if name not in GENERIC_LAUNCHERS:
            break
        if name in WRAPPERS and "--" in rest:
            # z. B. „gamescope -W 1920 -- steam“: Optionen samt Werten überspringen
            i = i + 1 + rest.index("--") + 1
            continue
        i += 1
    return result


def real_programs(exec_line: str) -> list[str]:
    """Nur die Wörter einer Exec-Zeile, die tatsächlich Programme sind.

    Nach einem Programm-Starter wie „wine“ oder „steam“ folgt ein Argument
    („start“, „steam://…“), kein Programm. Das zählt nur, wenn es ein
    vollständiger Pfad ist (z. B. „python3 /opt/tool/app.py“).
    """
    calls = exec_candidates(exec_line)
    if not calls:
        return []
    result = [calls[0]]
    for prev, tok in zip(calls, calls[1:]):
        if Path(prev).name in HANDLERS and not tok.startswith("/"):
            break
        result.append(tok)
    return result


def missing_program(exec_line: str) -> str:
    """Das erste Programm einer Exec-Zeile, das es nicht gibt – oder „“, wenn alles da ist."""
    return next((c for c in real_programs(exec_line) if not target_exists(c)), "")


def main_target(exec_line: str) -> str:
    """Das Programm, um das es in einer Exec-Zeile eigentlich geht.

    Starter wie Terminals oder „sh“ werden übersprungen – außer der Eintrag
    startet wirklich nur den Starter selbst (z. B. ein Eintrag für kitty).
    """
    calls = real_programs(exec_line)
    real = [c for c in calls if Path(c).name not in GENERIC_LAUNCHERS | TERMINALS]
    if real:
        return real[0]
    # Nur Starter: der innerste zählt („gamescope -- steam“ → steam, „kitty“ → kitty)
    return calls[-1] if calls else ""


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
            # /usr/bin/thunderbird ist z. B. nur eine Verknüpfung auf
            # /usr/lib/thunderbird/thunderbird – KDE schreibt in seine
            # „userapp-…“-Einträge oft den echten Pfad.
            real = os.path.realpath(exe)
            if real != exe:
                by_path.setdefault(real, []).append(prog)

    unmatched = []
    for e in entries:
        if e.file_id in assigned:
            continue
        target = main_target(e.exec)
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
    """Symbol-Vorschlag: aus einem vorhandenen (evtl. versteckten) Eintrag, sonst der Programmname."""
    for entry in prog.desktop_entries:
        if entry.icon:
            return entry.icon
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
    icon = icon.strip()
    if icon.startswith("/") and Path(icon).is_file() and not _is_within(Path(icon), user_icon_dir()):
        icon = str(install_icon(Path(icon), name))
    path.write_text(build_desktop_text(name, exec_line, icon, comment, categories, terminal), encoding="utf-8")
    path.chmod(0o644)
    refresh_menu_cache(target_dir)
    return path


def install_icon(src: Path, name: str) -> Path:
    """Kopiert ein Symbolbild in den eigenen Symbolordner.

    So funktioniert der Eintrag auch dann noch, wenn die Originaldatei (z. B. in
    „Downloads“) gelöscht wird.
    """
    suffix = src.suffix.lower()
    if suffix not in ICON_FORMATS:
        raise ValueError(f"Als Symbol gehen nur {', '.join(ICON_FORMATS)}-Dateien.")
    target_dir = user_icon_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{_slug(name)}{suffix}"
    counter = 2
    while target.exists():
        target = target_dir / f"{_slug(name)}-{counter}{suffix}"
        counter += 1
    shutil.copyfile(src, target)
    target.chmod(0o644)
    return target


def _is_within(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
        return True
    except (ValueError, OSError):
        return False


def is_user_entry(entry: DesktopEntry) -> bool:
    """Liegt der Eintrag in deinem eigenen Benutzerordner (nicht im System)?"""
    return _is_within(entry.path, user_applications_dir())


def origin_note(entry: DesktopEntry) -> str:
    """Kurze Erklärung, wer einen Eintrag typischerweise anlegt (sonst „“)."""
    if entry.file_id.startswith("userapp-"):
        return (
            "Von KDE angelegt, als eine Datei oder ein Link über „Öffnen mit …“ diesem "
            "Programm zugeordnet wurde. Versteckter Hilfseintrag, harmlos."
        )
    if entry.raw.get("X-AppImage-Version") or "appimagekit" in entry.file_id.lower():
        return "Von einem AppImage-Werkzeug angelegt."
    if "steam://" in entry.exec:
        return "Von Steam angelegte Spiele-Verknüpfung."
    return ""


def can_remove(entry: DesktopEntry) -> bool:
    """Darf der Software-Kompass diesen Eintrag löschen?

    Ja, wenn er ihn selbst angelegt hat oder der Eintrag in deinem
    Benutzerordner liegt. Systemeinträge (z. B. /usr/share/applications)
    gehören zu Paketen und werden nie angefasst.
    """
    return is_user_entry(entry)


def overridden_system_entry(entry: DesktopEntry) -> Path | None:
    """Überdeckt dieser Benutzereintrag einen gleichnamigen Systemeintrag?

    Dann taucht nach dem Löschen wieder der ursprüngliche Systemeintrag auf.
    """
    try:
        rel = entry.path.relative_to(user_applications_dir())
    except ValueError:
        return None
    for apps_dir in applications_dirs()[1:]:
        candidate = apps_dir / rel
        if candidate.is_file():
            return candidate
    return None


def remove_entry(entry: DesktopEntry) -> None:
    """Löscht einen Eintrag aus dem Benutzerordner (niemals Systemeinträge)."""
    if not can_remove(entry):
        raise PermissionError(
            "Dieser Eintrag gehört zum System bzw. zu einem Paket und wird vom Software-Kompass nicht gelöscht."
        )
    entry.path.unlink()
    # Ein von uns kopiertes Symbol wird mit aufgeräumt.
    if entry.created_by_us and entry.icon.startswith("/") and _is_within(Path(entry.icon), user_icon_dir()):
        Path(entry.icon).unlink(missing_ok=True)
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
