"""Tests für Einstufung und sichere Installation von Paketverwaltungen."""

import subprocess

from cachy_kompass import installers, terminal
from cachy_kompass.installers import SPECS, Rating, plan_install


def spec(name):
    return next(s for s in SPECS if s.name == name)


def test_discouraged_never_installable():
    everything = {p for s in SPECS for p in s.install_packages}
    for s in SPECS:
        if s.rating is Rating.DISCOURAGED:
            assert not s.install_packages and not s.install_flatpak, s.name
            assert plan_install(s, everything, flatpak_present=True)[0] is None


def test_every_tool_has_a_reason():
    assert all(s.reason for s in SPECS)


def test_install_only_from_official_repos():
    flatpak = spec("Flatpak")
    cmd, note = plan_install(flatpak, {"flatpak"}, flatpak_present=False)
    assert cmd == ["sudo", "pacman", "-S", "--needed", "flatpak"]
    # nicht in den Repos gefunden → kein Knopf, auch kein AUR
    cmd, note = plan_install(flatpak, set(), flatpak_present=False)
    assert cmd is None and "AUR" in note


def test_all_packages_must_be_available():
    distrobox = spec("Distrobox")
    assert plan_install(distrobox, {"distrobox"}, False)[0] is None
    assert plan_install(distrobox, {"distrobox", "podman"}, False)[0][-2:] == ["distrobox", "podman"]


def test_gearlever_falls_back_to_flathub():
    gl = spec("Gear Lever")
    assert plan_install(gl, set(), flatpak_present=True)[0] == ["flatpak", "install", "flathub", "it.mijorus.gearlever"]
    assert plan_install(gl, set(), flatpak_present=False)[0] is None
    assert plan_install(gl, {"gearlever"}, flatpak_present=True)[0][:3] == ["sudo", "pacman", "-S"]


def test_parse_si_names():
    out = "Repository      : extra\nName            : flatpak\nVersion         : 1.16-1\n\nRepository      : cachyos\nName            : paru\n"
    assert installers.parse_si_names(out) == {"flatpak", "paru"}


def test_detect_offers_install_for_missing(monkeypatch):
    monkeypatch.setattr(installers.util, "which", lambda name: None)
    monkeypatch.setattr(installers, "find_brew", lambda: None)
    monkeypatch.setattr(installers, "repo_available", lambda pkgs: {"flatpak"} & pkgs)
    statuses = {s.spec.name: s for s in installers.detect([])}
    assert statuses["Flatpak"].install_command[-1] == "flatpak"
    assert statuses["Snap (snapd)"].install_command is None
    assert statuses["Topgrade"].install_command is None  # in diesem Test nicht in den Repos


def test_terminal_script_runs_and_waits():
    script = terminal.build_script(["echo", "Hallo Welt"])
    out = subprocess.run(["bash", "-c", script], input="\n", capture_output=True, text=True, timeout=10).stdout
    assert "    echo 'Hallo Welt'" in out  # Befehl wird vorher angezeigt
    assert "Hallo Welt\n" in out and "✔ Fertig" in out
    failing = subprocess.run(["bash", "-c", terminal.build_script(["false"])], input="\n", capture_output=True, text=True, timeout=10).stdout
    assert "✘ Nicht erfolgreich" in failing


def test_terminal_argv_for_konsole():
    argv = terminal.terminal_argv(["sudo", "pacman", "-S", "flatpak"], ("/usr/bin/konsole", ["-e"]))
    assert argv[:4] == ["/usr/bin/konsole", "-e", "bash", "-c"]
    assert "sudo pacman -S flatpak" in argv[4]
