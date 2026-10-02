"""Tests für die Erkennung manuell installierter Programme."""

import pytest

from cachy_kompass.models import Program, Source
from cachy_kompass.sources import files
from cachy_kompass.sources.base import ScanContext


@pytest.fixture
def fake_system(tmp_path, monkeypatch):
    """Baut ein Mini-System mit /opt und /usr/local/bin im Testordner."""
    opt = tmp_path / "opt"
    local_bin = tmp_path / "usr" / "local" / "bin"
    for d in (opt / "teamspeak3", opt / "MeinTool", local_bin):
        d.mkdir(parents=True)
    (opt / "MeinTool" / "meintool").write_text("#!/bin/sh\n")
    (opt / "MeinTool" / "meintool").chmod(0o755)
    for name in ("mkinitcpio", "eigenes-skript"):
        (local_bin / name).write_text("#!/bin/sh\n")
        (local_bin / name).chmod(0o755)
    monkeypatch.setattr(files, "OPT_DIR", opt)
    monkeypatch.setattr(files, "MANUAL_BIN_DIRS", [local_bin])
    # „pacman -Qo“ soll hier nichts finden (wie wenn es fehlschlägt)
    monkeypatch.setattr(files.util, "pacman_owners", lambda paths: {})
    return opt, local_bin


def test_pacman_owned_paths_are_not_manual(fake_system):
    opt, local_bin = fake_system
    ctx = ScanContext(
        programs=[Program("mkinitcpio", "40-1", Source.REPO, executables=["/usr/bin/mkinitcpio"])],
        pacman_paths={str(opt / "teamspeak3" / "ts3client_linux_amd64")},
    )
    names = {p.name: p for p in files.ManualSource().scan(ctx)}
    # Ordner in /opt, in dem eine Datei einem Paket gehört → nicht manuell
    assert "teamspeak3" not in names
    # Echte Handarbeit wird weiterhin gefunden
    assert names["MeinTool"].executables == [str(opt / "MeinTool" / "meintool")]
    assert "eigenes-skript" in names
    # Gleichnamige Kopie eines Pakets bekommt einen deutlichen Hinweis
    assert "zusätzliche" in names["mkinitcpio"].origin


def test_symlink_to_pacman_file_is_not_manual(fake_system, tmp_path):
    _, local_bin = fake_system
    target = tmp_path / "usr" / "lib" / "real-tool"
    target.parent.mkdir(parents=True)
    target.write_text("#!/bin/sh\n")
    target.chmod(0o755)
    (local_bin / "tool-link").symlink_to(target)
    ctx = ScanContext(pacman_paths={str(target)})
    names = {p.name for p in files.ManualSource().scan(ctx)}
    assert "tool-link" not in names


def test_uninstall_commands(tmp_path, monkeypatch):
    from cachy_kompass.models import Program, Source

    monkeypatch.setattr(files.Path, "home", staticmethod(lambda: tmp_path))
    home_file = tmp_path / "bin" / "mein skript"
    home_file.parent.mkdir()
    home_file.write_text("x")
    assert Program("x", "?", Source.MANUAL, install_path=str(home_file)).uninstall_command() == f"rm '{home_file}'"
    opt_dir = tmp_path.parent / "opt-test" / "Tool"
    opt_dir.mkdir(parents=True)
    assert Program("Tool", "?", Source.MANUAL, install_path=str(opt_dir)).uninstall_command() == f"sudo rm -r {opt_dir}"


def test_finds_itself(tmp_path, monkeypatch):
    local_bin = tmp_path / ".local" / "bin"
    local_bin.mkdir(parents=True)
    launcher = local_bin / "cachy-kompass"
    launcher.write_text("#!/bin/sh\n")
    launcher.chmod(0o755)
    monkeypatch.setattr(files, "HOME", tmp_path)
    monkeypatch.setattr(files, "MANUAL_BIN_DIRS", [local_bin])
    monkeypatch.setattr(files, "OPT_DIR", tmp_path / "keins")
    monkeypatch.setattr(files.util, "pacman_owners", lambda paths: {})
    (me,) = files.ManualSource().scan(ScanContext())
    assert me.display_name == "Cachy Software-Kompass"
    assert me.uninstall_command().startswith("rm -rf ~/.local/share/cachy-kompass ")
