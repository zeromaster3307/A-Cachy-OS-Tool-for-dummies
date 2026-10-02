"""Fälle rund um Claude Code: npm, offizieller Installer, Einträge über Terminals, Suche."""

import json

from cachy_kompass import desktop
from cachy_kompass.models import MenuStatus, Program, Source
from cachy_kompass.sources.devtools import npm_bin_names
from cachy_kompass.sources.files import version_from_link


def test_exec_candidates_see_through_wrappers():
    assert desktop.main_target("konsole -e claude") == "claude"
    assert desktop.main_target("konsole --workdir /home/a -e claude --resume") == "claude"
    assert desktop.main_target("gnome-terminal -- claude") == "claude"
    assert desktop.main_target("kitty claude") == "claude"
    assert desktop.main_target("sh -c 'cd ~/Projekte && claude'") == "claude"
    assert desktop.main_target("env TERM=xterm-256color /home/a/.local/bin/claude %U") == "/home/a/.local/bin/claude"
    assert desktop.main_target("kitty") == "kitty"  # Eintrag für das Terminal selbst
    assert desktop.main_target("/usr/bin/firefox %u") == "/usr/bin/firefox"


def test_terminal_entry_belongs_to_program_not_terminal(tmp_path):
    apps = tmp_path / "applications"
    apps.mkdir()
    (apps / "claude-code.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Claude Code\nExec=konsole -e claude\nIcon=claude\n"
    )
    konsole = Program("konsole", "24", Source.REPO, executables=["/usr/bin/konsole"])
    claude = Program("@anthropic-ai/claude-code", "2.1.0", Source.NPM, executables=["/home/a/.npm-global/bin/claude"])
    desktop.match_entries([konsole, claude], desktop.load_entries([apps]))
    assert claude.menu_status is MenuStatus.VISIBLE
    assert konsole.menu_status is MenuStatus.NONE
    assert "claude code" in claude.search_text()


def test_npm_bin_names(tmp_path):
    pkg = tmp_path / "claude-code"
    pkg.mkdir()
    (pkg / "package.json").write_text(json.dumps({"name": "@anthropic-ai/claude-code", "bin": {"claude": "cli.js"}}))
    assert npm_bin_names(pkg) == ["claude"]
    (pkg / "package.json").write_text(json.dumps({"name": "@scope/tool", "bin": "cli.js"}))
    assert npm_bin_names(pkg) == ["tool"]
    assert npm_bin_names(tmp_path / "fehlt") == []


def test_version_from_link(tmp_path):
    versions = tmp_path / "share" / "claude" / "versions"
    versions.mkdir(parents=True)
    (versions / "2.1.42").write_text("binary")
    link = tmp_path / "claude"
    link.symlink_to(versions / "2.1.42")
    assert version_from_link(link) == "2.1.42"
    assert version_from_link(versions / "2.1.42") == ""  # keine Verknüpfung


def test_search_finds_menu_name():
    p = Program("claude", "2.1.42", Source.MANUAL, executables=["/home/a/.local/bin/claude"])
    p.desktop_entries = [desktop.entry_from_raw(desktop.Path("/x.desktop"), "x.desktop", {"Name": "Claude Code"})]
    text = p.search_text()
    assert all(w in text for w in "claude code".split())


def test_missing_program_no_false_alarms(monkeypatch):
    """Wine-, Steam- und Flatpak-Einträge sind nicht „kaputt“, nur weil danach ein Argument folgt."""
    installed = {"wine", "steam", "flatpak", "gamescope", "konsole", "claude", "ls", "sudo", "sh", "python3"}
    monkeypatch.setattr(desktop, "target_exists", lambda target: desktop.Path(target).name in installed)
    ok = [
        "wine start /unix %f",
        "steam steam://rungameid/570",
        "/usr/bin/flatpak run --branch=stable --arch=x86_64 --command=gimp org.gimp.GIMP @@u %U @@",
        "gamescope -W 1920 -H 1080 -- steam",
        "konsole -e claude",
        "sh -c 'cd ~/Projekte && export FOO=1 && claude'",
    ]
    for line in ok:
        assert desktop.missing_program(line) == "", line
    assert desktop.missing_program("gibtsnicht --flag") == "gibtsnicht"
    assert desktop.missing_program("konsole -e weg") == "weg"
    assert desktop.missing_program("sudo weg") == "weg"
    assert desktop.missing_program("python3 /opt/gibtsnicht/app.py") == "/opt/gibtsnicht/app.py"
    # Für die Zuordnung zählt bei Starter + Argument der Starter selbst, nicht „start“
    assert desktop.main_target("wine start /unix %f") == "wine"
    assert desktop.main_target("gamescope -W 1920 -- steam") == "steam"
