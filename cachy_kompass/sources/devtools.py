"""Programme aus Entwickler-Paketverwaltungen: cargo (Rust), npm (Node.js), Homebrew."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cachy_kompass import util
from cachy_kompass.models import Program, Source, UpdateResult, UpdateStatus
from cachy_kompass.sources.base import PackageSource, ScanContext, compare_result

CARGO_BIN = util.HOME / ".cargo" / "bin"
BREW_PATHS = ["/home/linuxbrew/.linuxbrew/bin/brew", str(util.HOME / ".linuxbrew" / "bin" / "brew")]


# --- cargo -------------------------------------------------------------------

_CARGO_RE = re.compile(r"^(\S+) v(\S+?)(?: \((.+)\))?:$")


def parse_cargo_list(text: str) -> list[dict]:
    """``cargo install --list``::

        ripgrep v14.1.0:
            rg
        tool v0.1.0 (https://github.com/x/tool#abc123):
            tool
    """
    rows: list[dict] = []
    for line in text.splitlines():
        m = _CARGO_RE.match(line)
        if m:
            rows.append({"name": m.group(1), "version": m.group(2), "from": m.group(3) or "", "bins": []})
        elif line.startswith((" ", "\t")) and rows:
            rows[-1]["bins"].append(line.strip())
    return rows


def crates_latest(name: str) -> str | None:
    try:
        return util.http_json(f"https://crates.io/api/v1/crates/{util.url_quote(name)}")["crate"]["max_stable_version"]
    except Exception:
        return None


class CargoSource(PackageSource):
    title = "cargo"
    handles = (Source.CARGO,)

    def is_available(self) -> bool:
        return util.which("cargo") is not None or CARGO_BIN.is_dir()

    def scan(self, ctx: ScanContext) -> list[Program]:
        if not util.which("cargo"):
            return []
        programs = []
        for row in parse_cargo_list(util.run(["cargo", "install", "--list"]) or ""):
            from_crates = not row["from"]
            programs.append(
                Program(
                    name=row["name"],
                    version=row["version"],
                    source=Source.CARGO,
                    origin="crates.io" if from_crates else f"Quellcode aus {row['from']}",
                    executables=[str(CARGO_BIN / b) for b in row["bins"]],
                    url=f"https://crates.io/crates/{row['name']}" if from_crates else "",
                    install_path="" if from_crates else row["from"],
                )
            )
        return programs

    def check_updates(self, programs: list[Program]) -> dict[str, UpdateResult]:
        results = {}
        from_crates = [p for p in programs if not p.install_path]
        for p in programs:
            if p.install_path:
                results[p.key] = UpdateResult(UpdateStatus.NOT_CHECKABLE, note="Direkt aus einem Git-Repo/Ordner gebaut.")
        with ThreadPoolExecutor(max_workers=4) as pool:
            for p, latest in zip(from_crates, pool.map(lambda p: crates_latest(p.name), from_crates)):
                results[p.key] = compare_result(p.version, latest, "" if latest else "crates.io nicht erreichbar.")
        return results


# --- npm ---------------------------------------------------------------------


def parse_npm_ls(text: str) -> dict[str, str]:
    """``npm ls -g --depth=0 --json`` → {Paket: Version}."""
    try:
        deps = json.loads(text).get("dependencies", {})
    except (json.JSONDecodeError, AttributeError):
        return {}
    return {name: info.get("version", "") for name, info in deps.items()}


def parse_npm_outdated(text: str) -> dict[str, str]:
    """``npm outdated -g --json`` → {Paket: neueste Version}."""
    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
    return {name: info.get("latest", "") for name, info in data.items() if isinstance(info, dict)}


class NpmSource(PackageSource):
    title = "npm"
    handles = (Source.NPM,)

    def is_available(self) -> bool:
        return util.which("npm") is not None

    def scan(self, ctx: ScanContext) -> list[Program]:
        packages = parse_npm_ls(util.run(["npm", "ls", "-g", "--depth=0", "--json"], ok_codes=(0, 1)) or "")
        root = (util.run(["npm", "root", "-g"]) or "").strip()
        paths = {name: str(Path(root) / name) for name in packages} if root else {}
        # Unter Arch landen auch von pacman installierte Node-Pakete (z. B. npm
        # selbst) im globalen Ordner. Die zählen wir nicht doppelt.
        owned = util.pacman_owners(paths.values())
        return [
            Program(
                name=name,
                version=version,
                source=Source.NPM,
                origin="npm-Registry",
                install_path=paths.get(name, ""),
                url=f"https://www.npmjs.com/package/{name}",
            )
            for name, version in packages.items()
            if paths.get(name) not in owned
        ]

    def check_updates(self, programs: list[Program]) -> dict[str, UpdateResult]:
        # npm outdated endet mit Code 1, wenn es Updates gibt.
        out = util.run(["npm", "outdated", "-g", "--json"], timeout=180, ok_codes=(0, 1))
        if out is None:
            return {p.key: UpdateResult(UpdateStatus.UNKNOWN, note="npm-Registry nicht erreichbar.") for p in programs}
        outdated = parse_npm_outdated(out)
        return {
            p.key: UpdateResult(UpdateStatus.OUTDATED, outdated[p.name])
            if p.name in outdated
            else UpdateResult(UpdateStatus.CURRENT, p.version)
            for p in programs
        }


# --- Homebrew ----------------------------------------------------------------


def parse_brew_versions(text: str) -> dict[str, str]:
    """``brew list --versions`` → {Formel: Version}."""
    result = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            result[parts[0]] = parts[-1]
    return result


def parse_brew_outdated(text: str) -> dict[str, str]:
    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
    return {f["name"]: f.get("current_version", "") for f in data.get("formulae", []) + data.get("casks", [])}


def find_brew() -> str | None:
    return util.which("brew") or next((p for p in BREW_PATHS if Path(p).exists()), None)


class BrewSource(PackageSource):
    title = "Homebrew"
    handles = (Source.BREW,)

    def is_available(self) -> bool:
        return find_brew() is not None

    def scan(self, ctx: ScanContext) -> list[Program]:
        brew = find_brew()
        prefix = str(Path(brew).parent) if brew else ""
        versions = parse_brew_versions(util.run([brew, "list", "--versions"]) or "") if brew else {}
        return [
            Program(
                name=name,
                version=version,
                source=Source.BREW,
                origin="Homebrew",
                executables=[f"{prefix}/{name}"] if prefix else [],
                url=f"https://formulae.brew.sh/formula/{name}",
            )
            for name, version in versions.items()
        ]

    def check_updates(self, programs: list[Program]) -> dict[str, UpdateResult]:
        brew = find_brew()
        out = util.run([brew, "outdated", "--json=v2"], timeout=300) if brew else None
        if out is None:
            return {p.key: UpdateResult(UpdateStatus.UNKNOWN, note="Homebrew-Prüfung fehlgeschlagen.") for p in programs}
        outdated = parse_brew_outdated(out)
        return {
            p.key: UpdateResult(UpdateStatus.OUTDATED, outdated[p.name])
            if p.name in outdated
            else UpdateResult(UpdateStatus.CURRENT, p.version)
            for p in programs
        }
