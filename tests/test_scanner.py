"""Tests für das Zusammenspiel der Quellen, ohne echte Paketverwaltungen."""

from cachy_kompass import scanner
from cachy_kompass.models import Program, Source, UpdateResult, UpdateStatus
from cachy_kompass.sources.base import PackageSource


class FakeSource(PackageSource):
    title = "Test"
    handles = (Source.REPO,)

    def is_available(self):
        return True

    def scan(self, ctx):
        return [Program("zeta", "1", Source.REPO), Program("alpha", "2", Source.REPO, explicit=False)]

    def check_updates(self, programs):
        return {p.key: UpdateResult(UpdateStatus.OUTDATED, "9") for p in programs}


class BrokenSource(PackageSource):
    title = "Kaputt"

    def is_available(self):
        return True

    def scan(self, ctx):
        raise RuntimeError("geht nicht")


def test_scan_collects_and_survives_errors(monkeypatch):
    monkeypatch.setattr(scanner.desktop, "load_entries", lambda: [])
    result = scanner.scan(sources=[FakeSource(), BrokenSource()])
    assert [p.name for p in result.programs] == ["alpha", "zeta"]  # sortiert
    assert result.warnings and "Kaputt" in result.warnings[0]


def test_check_updates_routes_to_source():
    progs = [Program("zeta", "1", Source.REPO), Program("x.AppImage", "?", Source.APPIMAGE)]
    results = scanner.check_updates(progs, sources=[FakeSource()])
    assert results["repo:zeta"].status is UpdateStatus.OUTDATED
    assert "appimage:x.AppImage" not in results  # keine zuständige Quelle übergeben
    scanner.apply_updates(progs, results)
    assert progs[0].update.latest == "9"
    assert progs[1].update.status is UpdateStatus.NOT_CHECKED
