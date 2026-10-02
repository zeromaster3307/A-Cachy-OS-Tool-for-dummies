"""Python-Programme, installiert mit pipx oder ``uv tool``."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor

from cachy_kompass import util
from cachy_kompass.models import Program, Source, UpdateResult
from cachy_kompass.sources.base import PackageSource, ScanContext, compare_result

LOCAL_BIN = util.HOME / ".local" / "bin"


def pypi_latest(package: str) -> str | None:
    try:
        return util.http_json(f"https://pypi.org/pypi/{util.url_quote(package)}/json")["info"]["version"]
    except Exception:
        return None


def check_pypi(programs: list[Program]) -> dict[str, UpdateResult]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        latest = dict(zip((p.key for p in programs), pool.map(lambda p: pypi_latest(p.name), programs)))
    return {p.key: compare_result(p.version, latest[p.key], "" if latest[p.key] else "PyPI nicht erreichbar.") for p in programs}


def parse_pipx_json(text: str) -> list[dict]:
    """``pipx list --json`` → [{name, version, apps}]."""
    try:
        venvs = json.loads(text).get("venvs", {})
    except (json.JSONDecodeError, AttributeError):
        return []
    rows = []
    for venv_name, venv in venvs.items():
        main = venv.get("metadata", {}).get("main_package", {})
        rows.append(
            {
                "name": main.get("package") or venv_name,
                "version": main.get("package_version", ""),
                "apps": main.get("apps", []),
            }
        )
    return rows


def parse_uv_list(text: str) -> list[dict]:
    """``uv tool list``::

        black v24.1.0
        - black
        - blackd
    """
    rows: list[dict] = []
    for line in text.splitlines():
        m = re.match(r"^(\S+) v(\S+)", line)
        if m:
            rows.append({"name": m.group(1), "version": m.group(2), "apps": []})
        elif line.startswith("- ") and rows:
            rows[-1]["apps"].append(line[2:].strip())
    return rows


class _PythonToolSource(PackageSource):
    source: Source
    cmd: str

    def is_available(self) -> bool:
        return util.which(self.cmd) is not None

    def _rows(self) -> list[dict]:
        raise NotImplementedError

    def scan(self, ctx: ScanContext) -> list[Program]:
        return [
            Program(
                name=row["name"],
                version=row["version"],
                source=self.source,
                origin="PyPI (Python-Paketindex)",
                executables=[str(LOCAL_BIN / app) for app in row["apps"]],
                url=f"https://pypi.org/project/{row['name']}/",
            )
            for row in self._rows()
        ]

    def check_updates(self, programs: list[Program]) -> dict[str, UpdateResult]:
        return check_pypi(programs)


class PipxSource(_PythonToolSource):
    title = "pipx"
    source = Source.PIPX
    handles = (Source.PIPX,)
    cmd = "pipx"

    def _rows(self) -> list[dict]:
        return parse_pipx_json(util.run(["pipx", "list", "--json"]) or "")


class UvToolSource(_PythonToolSource):
    title = "uv tool"
    source = Source.UV
    handles = (Source.UV,)
    cmd = "uv"

    def _rows(self) -> list[dict]:
        return parse_uv_list(util.run(["uv", "tool", "list"]) or "")
