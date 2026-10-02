"""Tests für den Reiter „Aufräumen“ – ohne echtes pacman/flatpak."""

import pytest

from cachy_kompass import cleanup, terminal
from cachy_kompass.cleanup import Action
from cachy_kompass.models import DesktopEntry, Program, Source


@pytest.fixture
def fake_tools(monkeypatch):
    """Simuliert vorhandene Befehle und deren Ausgaben."""
    outputs: dict[str, str] = {}
    available: set[str] = set()
    monkeypatch.setattr(cleanup.util, "which", lambda name: f"/usr/bin/{name}" if name in available else None)
    monkeypatch.setattr(cleanup.util, "run", lambda cmd, **kw: outputs.get(" ".join(cmd)))
    return outputs, available


def test_parse_paccache_dry_run():
    assert cleanup.parse_paccache_dry_run("==> finished dry run: 12 candidates (disk space saved: 845.21 MiB)") == (12, cleanup.util.parse_size("845.21 MiB"))
    assert cleanup.parse_paccache_dry_run("==> finished dry run: 1 candidate (disk space saved: 2.00 GiB)")[0] == 1
    assert cleanup.parse_paccache_dry_run("==> no candidate packages found for pruning") == (0, 0)


def test_orphans(fake_tools):
    outputs, available = fake_tools
    available.add("pacman")
    outputs["pacman -Qdtq"] = "libfoo\npython-old\n"
    programs = [Program("libfoo", "1", Source.REPO, explicit=False, size_bytes=2 * 1024**2)]
    item = cleanup.check_orphans(programs)
    assert item.found and item.action is Action.TERMINAL
    assert item.commands == [["sudo", "pacman", "-Rns", "libfoo", "python-old"]]
    assert item.size == 2 * 1024**2 and "libfoo  (2,0 MB)" in item.details


def test_no_orphans(fake_tools):
    _, available = fake_tools
    available.add("pacman")
    item = cleanup.check_orphans([])
    assert not item.found and item.action is Action.NONE and item.summary == "keine"


def test_package_cache(fake_tools, tmp_path, monkeypatch):
    outputs, available = fake_tools
    cache = tmp_path / "pkg"
    cache.mkdir()
    (cache / "foo-1.0-1-x86_64.pkg.tar.zst").write_bytes(b"x" * 1000)
    monkeypatch.setattr(cleanup, "PACMAN_CACHE", cache)
    # ohne paccache: Hinweis auf pacman-contrib, kein Knopf
    item = cleanup.check_package_cache()
    assert item.action is Action.NONE and "pacman-contrib" in item.manual_command
    # mit paccache: Trockenlauf wird ausgewertet
    available.add("paccache")
    outputs["paccache -d -k2"] = "==> finished dry run: 5 candidates (disk space saved: 1.00 GiB)"
    outputs["paccache -du -k0"] = "==> finished dry run: 2 candidates (disk space saved: 100.00 MiB)"
    item = cleanup.check_package_cache()
    assert item.action is Action.TERMINAL and item.size == 1024**3 + 100 * 1024**2
    assert item.commands[0] == ["sudo", "paccache", "-r", "-k2"]


def test_aur_build_cache(tmp_path, monkeypatch):
    clone = tmp_path / "paru" / "clone" / "somepkg"
    clone.mkdir(parents=True)
    (clone / "src.tar.gz").write_bytes(b"x" * 2048)
    monkeypatch.setattr(cleanup, "AUR_BUILD_CACHES", [tmp_path / "paru" / "clone", tmp_path / "yay"])
    item = cleanup.check_aur_build_cache()
    assert item.size == 2048 and item.commands == [["rm", "-rf", str(tmp_path / "paru" / "clone")]]
    assert "sudo" not in terminal.describe(item.commands)  # Benutzerordner → kein sudo


def test_broken_entries(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(cleanup.desktop, "target_exists", lambda t: t != "weg")
    user = DesktopEntry(path=tmp_path / "applications" / "alt.desktop", file_id="alt.desktop", name="Alt", exec="weg %f")
    system = DesktopEntry(path=tmp_path / "sys" / "x.desktop", file_id="x.desktop", name="X", exec="weg")
    ok = DesktopEntry(path=tmp_path / "applications" / "ok.desktop", file_id="ok.desktop", name="Ok", exec="da")
    item = cleanup.check_broken_entries([user, system, ok])
    assert item.summary == "2 Einträge"
    assert item.entries == [user]  # nur der Benutzereintrag wird entfernt
    assert item.action is Action.REMOVE_ENTRIES


def test_not_in_aur(monkeypatch):
    programs = [Program("da-pkg", "1", Source.AUR), Program("weg-pkg", "1", Source.AUR), Program("vim", "9", Source.REPO)]
    monkeypatch.setattr(cleanup.util, "http_json", lambda url: {"results": [{"Name": "da-pkg"}]})
    item = cleanup.check_not_in_aur(programs)
    assert item.details == ["weg-pkg"]
    assert item.action is Action.NONE  # bewusst kein Knopf
    assert item.manual_command == "sudo pacman -Rns weg-pkg"


def test_not_in_aur_offline(monkeypatch):
    def boom(url):
        raise OSError("kein Netz")

    monkeypatch.setattr(cleanup.util, "http_json", boom)
    item = cleanup.check_not_in_aur([Program("x", "1", Source.AUR)])
    assert item.summary == "nicht prüfbar" and not item.found


def test_scan_survives_failing_check(monkeypatch):
    def broken():
        raise RuntimeError("kaputt")

    monkeypatch.setattr(cleanup, "check_package_cache", broken)
    monkeypatch.setattr(cleanup.util, "which", lambda name: None)
    items = cleanup.scan([], [])
    assert any(i.summary == "Fehler" for i in items)
    assert any(i.key == "entries" for i in items)


def test_terminal_runs_several_commands():
    import subprocess

    script = terminal.build_script([["echo", "eins"], ["echo", "zwei"]])
    out = subprocess.run(["bash", "-c", script], input="\n", capture_output=True, text=True, timeout=10).stdout
    assert "folgende Befehle werden" in out and "eins\nzwei\n" in out and "✔ Fertig" in out
    # schlägt der erste fehl, läuft der zweite nicht
    out = subprocess.run(["bash", "-c", terminal.build_script([["false"], ["echo", "nie"]])],
                         input="\n", capture_output=True, text=True, timeout=10).stdout
    assert "nie\n" not in out.split("ausgeführt:")[1].split("\n\n", 2)[-1] and "✘" in out
