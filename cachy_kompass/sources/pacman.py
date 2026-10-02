"""pacman: offizielle Repos (CachyOS, Arch) und das AUR.

Woher wir was wissen:
  * ``pacman -Qi``  – alle installierten Pakete mit Beschreibung, Version, Grund
  * ``pacman -Qqm`` – „fremde“ Pakete, die in keinem Repo stehen (= AUR/selbst gebaut)
  * ``pacman -Sl``  – in welchem Repo ein Paket steht (z. B. cachyos-v3, extra)
  * ``pacman -Ql``  – welche Dateien (Programme, Startmenü-Einträge) zu einem Paket gehören
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

from cachy_kompass import util
from cachy_kompass.models import Program, Source, UpdateResult, UpdateStatus
from cachy_kompass.sources.base import PackageSource, ScanContext

AUR_RPC = "https://aur.archlinux.org/rpc/v5/info"
AUR_CHUNK = 100

_FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z ]*?)\s*:\s?(.*)$")


def parse_qi(text: str) -> list[dict[str, str]]:
    """Wertet die Ausgabe von ``pacman -Qi`` in eine Liste von Feldern aus."""
    packages: list[dict[str, str]] = []
    current: dict[str, str] = {}
    last_key = ""
    for line in text.splitlines():
        if not line.strip():
            if current:
                packages.append(current)
            current, last_key = {}, ""
            continue
        if line[0].isspace():
            # Fortsetzungszeile (z. B. weitere optionale Abhängigkeiten)
            if last_key:
                current[last_key] += " " + line.strip()
            continue
        m = _FIELD_RE.match(line)
        if m:
            last_key = m.group(1).strip()
            current[last_key] = m.group(2).strip()
    if current:
        packages.append(current)
    return packages


def parse_sl(text: str) -> dict[str, tuple[str, str]]:
    """``pacman -Sl`` → {Paketname: (Repo, Version im Repo)}.

    Steht ein Paket in mehreren Repos, gewinnt das erste – genau wie bei pacman
    selbst (Reihenfolge aus /etc/pacman.conf).
    """
    result: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        repo, name, version = parts[0], parts[1], parts[2]
        result.setdefault(name, (repo, version))
    return result


def parse_ql(text: str) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """``pacman -Ql`` → (Programmdateien je Paket, .desktop-Dateien je Paket)."""
    exes: dict[str, list[str]] = {}
    desktops: dict[str, list[str]] = {}
    for line in text.splitlines():
        pkg, _, path = line.partition(" ")
        if not path or path.endswith("/"):
            continue
        if path.startswith("/usr/bin/"):
            exes.setdefault(pkg, []).append(path)
        elif path.startswith("/usr/share/applications/") and path.endswith(".desktop"):
            desktops.setdefault(pkg, []).append(path)
    return exes, desktops


def parse_checkupdates(text: str) -> dict[str, str]:
    """``checkupdates`` → {Paket: neue Version}. Zeilenformat: ``foo 1.0-1 -> 1.1-1``."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[2] == "->":
            result[parts[0]] = parts[3]
    return result


def describe_repo(repo: str) -> str:
    """Übersetzt Repo-Namen in etwas Verständliches."""
    if repo.startswith("cachyos"):
        suffix = repo.removeprefix("cachyos").strip("-")
        detail = {
            "": "",
            "v3": "für moderne CPUs (x86-64-v3) optimiert",
            "core-v3": "Kernsystem, für x86-64-v3 optimiert",
            "extra-v3": "für x86-64-v3 optimiert",
            "v4": "für sehr moderne CPUs (x86-64-v4) optimiert",
            "core-v4": "Kernsystem, für x86-64-v4 optimiert",
            "extra-v4": "für x86-64-v4 optimiert",
            "znver4": "für AMD Zen 4/5 optimiert",
            "core-znver4": "Kernsystem, für AMD Zen 4/5 optimiert",
            "extra-znver4": "für AMD Zen 4/5 optimiert",
        }.get(suffix, "")
        return f"CachyOS-Repo „{repo}“" + (f" ({detail})" if detail else "")
    if repo in {"core", "extra", "multilib", "core-testing", "extra-testing", "multilib-testing"}:
        return f"Arch-Linux-Repo „{repo}“"
    if repo == "chaotic-aur":
        return "Chaotic-AUR (nachträglich hinzugefügtes Zusatz-Repo mit fertig gebauten AUR-Paketen)"
    return f"Repo „{repo}“ (nachträglich hinzugefügt)"


class PacmanSource(PackageSource):
    title = "pacman (Repos & AUR)"
    handles = (Source.REPO, Source.AUR)

    def is_available(self) -> bool:
        return util.which("pacman") is not None

    def scan(self, ctx: ScanContext) -> list[Program]:
        info = parse_qi(util.run(["pacman", "-Qi"]) or "")
        foreign = set((util.run(["pacman", "-Qqm"], ok_codes=(0, 1)) or "").split())
        repos = parse_sl(util.run(["pacman", "-Sl"]) or "")
        exes, desktops = parse_ql(util.run(["pacman", "-Ql"], timeout=300) or "")

        programs = []
        for pkg in info:
            name = pkg.get("Name", "")
            if not name:
                continue
            is_aur = name in foreign
            repo = repos.get(name, ("", ""))[0]
            programs.append(
                Program(
                    name=name,
                    version=pkg.get("Version", ""),
                    source=Source.AUR if is_aur else Source.REPO,
                    description=pkg.get("Description", ""),
                    origin="AUR bzw. selbst gebaut" if is_aur else describe_repo(repo),
                    explicit=pkg.get("Install Reason", "").startswith("Explicitly"),
                    executables=exes.get(name, []),
                    owned_desktop_files=desktops.get(name, []),
                    url=pkg.get("URL", ""),
                    install_date=pkg.get("Install Date", ""),
                )
            )
        return programs

    # --- Updates -------------------------------------------------------------

    def check_updates(self, programs: list[Program]) -> dict[str, UpdateResult]:
        results: dict[str, UpdateResult] = {}
        repo_pkgs = [p for p in programs if p.source is Source.REPO]
        aur_pkgs = [p for p in programs if p.source is Source.AUR]
        results.update(self._check_repo(repo_pkgs))
        results.update(self._check_aur(aur_pkgs))
        return results

    def _check_repo(self, programs: list[Program]) -> dict[str, UpdateResult]:
        if not programs:
            return {}
        if util.which("checkupdates"):
            # checkupdates (aus pacman-contrib) lädt eine frische Paketliste in
            # einen temporären Ordner – ohne root und ohne das System zu ändern.
            # Code 2 bedeutet „keine Updates“.
            out = util.run(["checkupdates"], timeout=300, ok_codes=(0, 2))
            if out is not None:
                updates = parse_checkupdates(out)
                return {
                    p.key: UpdateResult(UpdateStatus.OUTDATED, updates[p.name])
                    if p.name in updates
                    else UpdateResult(UpdateStatus.CURRENT, p.version)
                    for p in programs
                }
        # Rückfall: mit der lokal gespeicherten Paketliste vergleichen. Die ist
        # nur so aktuell wie das letzte „pacman -Sy“.
        repos = parse_sl(util.run(["pacman", "-Sl"]) or "")
        note = "Vergleich mit der zuletzt heruntergeladenen Paketliste (für genaue Prüfung: pacman-contrib installieren)."
        results = {}
        for p in programs:
            latest = repos.get(p.name, ("", ""))[1]
            if not latest:
                results[p.key] = UpdateResult(UpdateStatus.UNKNOWN, note="Nicht mehr in einem Repo gefunden.")
            elif util.vercmp(latest, p.version) > 0:
                results[p.key] = UpdateResult(UpdateStatus.OUTDATED, latest, note)
            else:
                results[p.key] = UpdateResult(UpdateStatus.CURRENT, latest, note)
        return results

    def _check_aur(self, programs: list[Program]) -> dict[str, UpdateResult]:
        """Fragt die Versionen direkt beim AUR ab (funktioniert ohne paru/yay)."""
        if not programs:
            return {}
        chunks = [programs[i : i + AUR_CHUNK] for i in range(0, len(programs), AUR_CHUNK)]
        aur_versions: dict[str, str] = {}
        failed = False

        def fetch(chunk: list[Program]) -> dict[str, str]:
            query = "&".join(f"arg[]={util.url_quote(p.name)}" for p in chunk)
            data = util.http_json(f"{AUR_RPC}?{query}")
            return {r["Name"]: r["Version"] for r in data.get("results", [])}

        with ThreadPoolExecutor(max_workers=4) as pool:
            for future in [pool.submit(fetch, c) for c in chunks]:
                try:
                    aur_versions.update(future.result())
                except Exception:  # Netzwerkfehler o. ä.
                    failed = True

        results = {}
        for p in programs:
            latest = aur_versions.get(p.name)
            if latest is None:
                note = "AUR nicht erreichbar." if failed else "Nicht (mehr) im AUR – evtl. selbst gebaut oder verwaist."
                results[p.key] = UpdateResult(UpdateStatus.UNKNOWN, note=note)
            elif re.search(r"-(git|svn|hg|bzr|nightly)$", p.name):
                results[p.key] = UpdateResult(
                    UpdateStatus.UNKNOWN,
                    latest,
                    "Entwicklerversion (-git o. ä.): baut immer den neuesten Stand, "
                    "die Versionsnummer im AUR ist nicht aussagekräftig.",
                )
            elif util.vercmp(latest, p.version) > 0:
                results[p.key] = UpdateResult(UpdateStatus.OUTDATED, latest)
            else:
                results[p.key] = UpdateResult(UpdateStatus.CURRENT, latest)
        return results
