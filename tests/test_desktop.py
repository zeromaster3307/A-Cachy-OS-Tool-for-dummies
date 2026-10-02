"""Tests für Startmenü-Einträge: lesen, zuordnen, anlegen, löschen."""

import pytest

from cachy_kompass import desktop
from cachy_kompass.models import MenuStatus, Program, Source


@pytest.fixture(autouse=True)
def no_menu_refresh(monkeypatch):
    """In Tests nicht wirklich das Startmenü neu aufbauen lassen."""
    monkeypatch.setattr(desktop, "refresh_menu_cache", lambda _dir: None)
    monkeypatch.setenv("LANG", "de_DE.UTF-8")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_parse_and_localize(tmp_path):
    text = """\
[Desktop Entry]
Type=Application
Name=Text Editor
Name[de]=Texteditor
Exec=kate %U
NoDisplay=false

[Desktop Action new-window]
Name=New Window
Exec=kate --new
"""
    raw = desktop.parse_desktop_text(text)
    assert raw["Exec"] == "kate %U"  # die Aktion überschreibt nichts
    entry = desktop.entry_from_raw(tmp_path / "x.desktop", "x.desktop", raw)
    assert entry.name == "Texteditor"
    assert entry.visible


def test_user_dir_overrides_system(tmp_path):
    user = tmp_path / "user" / "applications"
    system = tmp_path / "system" / "applications"
    write(system / "vlc.desktop", "[Desktop Entry]\nType=Application\nName=VLC\nExec=vlc\n")
    write(user / "vlc.desktop", "[Desktop Entry]\nType=Application\nName=VLC\nExec=vlc\nNoDisplay=true\n")
    write(system / "kde" / "foo.desktop", "[Desktop Entry]\nType=Application\nName=Foo\nExec=foo\n")
    entries = {e.file_id: e for e in desktop.load_entries([user, system])}
    assert entries["vlc.desktop"].no_display  # Benutzerdatei gewinnt
    assert "kde-foo.desktop" in entries  # Unterordner → „-“ in der Kennung


def test_exec_target():
    assert desktop.exec_target("/usr/bin/firefox %u") == "/usr/bin/firefox"
    assert desktop.exec_target("env GDK_BACKEND=x11 code --flag") == "code"
    assert desktop.exec_target('"/home/u/My Apps/x.AppImage" %F') == "/home/u/My Apps/x.AppImage"
    assert desktop.exec_target("") == ""


def test_match_entries(tmp_path):
    apps = tmp_path / "applications"
    write(apps / "firefox.desktop", "[Desktop Entry]\nType=Application\nName=Firefox\nExec=/usr/lib/firefox/firefox %u\n")
    write(apps / "org.gimp.GIMP.desktop", "[Desktop Entry]\nType=Application\nName=GIMP\nExec=/usr/bin/flatpak run org.gimp.GIMP\nX-Flatpak=org.gimp.GIMP\n")
    write(apps / "my-rg.desktop", "[Desktop Entry]\nType=Application\nName=Ripgrep\nExec=rg\nTerminal=true\n")
    write(apps / "helper.desktop", "[Desktop Entry]\nType=Application\nName=Helper\nExec=helper\nNoDisplay=true\n")
    write(apps / "broken.desktop", "[Desktop Entry]\nType=Application\nName=Weg\nExec=sh -c gibtsnicht\n")

    ff = Program("firefox", "131", Source.REPO, owned_desktop_files=["/usr/share/applications/firefox.desktop"])
    gimp = Program("org.gimp.GIMP", "2.10", Source.FLATPAK, display_name="GIMP")
    rg = Program("ripgrep", "14", Source.CARGO, executables=["/home/u/.cargo/bin/rg"])
    helper = Program("helper", "1", Source.REPO, executables=["/usr/bin/helper"])
    bash = Program("bash", "5", Source.REPO, executables=["/usr/bin/sh", "/usr/bin/bash"])
    lonely = Program("lonely", "1", Source.REPO, executables=["/usr/bin/lonely"])

    unmatched = desktop.match_entries([ff, gimp, rg, helper, bash, lonely], desktop.load_entries([apps]))

    assert ff.menu_status is MenuStatus.VISIBLE
    assert ff.display_name == "Firefox"
    assert gimp.menu_status is MenuStatus.VISIBLE
    assert rg.menu_status is MenuStatus.VISIBLE
    assert helper.menu_status is MenuStatus.HIDDEN
    assert lonely.menu_status is MenuStatus.NONE
    # „sh -c …“ darf nicht dem Paket bash zugeordnet werden
    assert bash.menu_status is MenuStatus.NONE
    assert [e.file_id for e in unmatched] == ["broken.desktop"]


def test_create_and_remove(tmp_path):
    apps = tmp_path / "applications"
    path = desktop.create_entry(
        "Mein Tool", '"/opt/mein tool/run"', icon="utilities-terminal",
        comment="Zeile1\nZeile2", categories=["Utility"], terminal=True, target_dir=apps,
    )
    assert path.name == "cachy-kompass-mein-tool.desktop"
    text = path.read_text()
    assert "Comment=Zeile1 Zeile2\n" in text  # keine Zeilenumbrüche im Wert
    assert "Terminal=true" in text and "Categories=Utility;" in text

    second = desktop.create_entry("Mein Tool", "x", target_dir=apps)
    assert second.name == "cachy-kompass-mein-tool-2.desktop"  # nichts überschreiben

    entry = next(e for e in desktop.load_entries([apps]) if e.path == path)
    assert entry.created_by_us
    assert desktop.exec_target(entry.exec) == "/opt/mein tool/run"
    desktop.remove_entry(entry)
    assert not path.exists()


def test_refuses_to_remove_foreign_entry(tmp_path):
    apps = tmp_path / "applications"
    write(apps / "vlc.desktop", "[Desktop Entry]\nType=Application\nName=VLC\nExec=vlc\n")
    entry = desktop.load_entries([apps])[0]
    with pytest.raises(PermissionError):
        desktop.remove_entry(entry)
    assert entry.path.exists()


def test_create_requires_values(tmp_path):
    with pytest.raises(ValueError):
        desktop.create_entry(" ", "x", target_dir=tmp_path)


def test_quote_exec_arg():
    assert desktop.quote_exec_arg("/usr/bin/foo") == "/usr/bin/foo"
    assert desktop.quote_exec_arg("/home/u/My App") == '"/home/u/My App"'
    assert desktop.quote_exec_arg('/a/"b"$') == '"/a/\\"b\\"\\$"'


def test_suggestions():
    assert desktop.suggest_exec(Program("org.gimp.GIMP", "1", Source.FLATPAK)) == "flatpak run org.gimp.GIMP"
    rg = Program("ripgrep", "14", Source.CARGO, executables=["/home/u/.cargo/bin/rg"])
    assert desktop.suggest_exec(rg) == "/home/u/.cargo/bin/rg"
    multi = Program("foo", "1", Source.REPO, executables=["/usr/bin/foo-helper", "/usr/bin/foo"])
    assert desktop.suggest_exec(multi) == "/usr/bin/foo"
