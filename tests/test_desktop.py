"""Tests für Startmenü-Einträge: lesen, zuordnen, anlegen, löschen."""

from pathlib import Path

import pytest

from cachy_kompass import desktop
from cachy_kompass.models import MenuStatus, Program, Source


@pytest.fixture(autouse=True)
def no_menu_refresh(monkeypatch, tmp_path):
    """In Tests nicht wirklich das Startmenü neu aufbauen lassen; Benutzerordner = Testordner."""
    monkeypatch.setattr(desktop, "refresh_menu_cache", lambda _dir: None)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "system"))
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


def test_refuses_to_remove_system_entry(tmp_path):
    apps = tmp_path / "system" / "applications"
    write(apps / "vlc.desktop", "[Desktop Entry]\nType=Application\nName=VLC\nExec=vlc\n")
    entry = desktop.load_entries([apps])[0]
    assert not desktop.can_remove(entry)
    with pytest.raises(PermissionError):
        desktop.remove_entry(entry)
    assert entry.path.exists()


def test_removes_hand_made_user_entry(tmp_path):
    """Selbst (z. B. mit Claude) angelegte Einträge im Benutzerordner dürfen weg."""
    user = tmp_path / "applications"
    system = tmp_path / "system" / "applications"
    write(user / "tailscale-tray.desktop", "[Desktop Entry]\nType=Application\nName=Tailscale Tray\nExec=tailscale-systray\n")
    write(user / "vlc.desktop", "[Desktop Entry]\nType=Application\nName=VLC\nExec=vlc\nNoDisplay=true\n")
    write(system / "vlc.desktop", "[Desktop Entry]\nType=Application\nName=VLC\nExec=vlc\n")
    entries = {e.file_id: e for e in desktop.load_entries()}
    tray = entries["tailscale-tray.desktop"]
    assert desktop.can_remove(tray) and not tray.created_by_us
    assert desktop.overridden_system_entry(tray) is None
    # Benutzereintrag, der einen Systemeintrag überdeckt → Hinweis möglich
    assert desktop.overridden_system_entry(entries["vlc.desktop"]) == system / "vlc.desktop"
    desktop.remove_entry(tray)
    assert not tray.path.exists()


def test_icon_file_is_copied_and_cleaned_up(tmp_path):
    logo = write(tmp_path / "Downloads" / "logo.svg", "<svg xmlns='http://www.w3.org/2000/svg'/>")
    path = desktop.create_entry("Mein Tool", "/bin/true", icon=str(logo))
    entry = next(e for e in desktop.load_entries() if e.path == path)
    copied = Path(entry.icon)
    assert copied.parent == desktop.user_icon_dir() and copied.suffix == ".svg"
    logo.unlink()  # Original weg – das Symbol bleibt trotzdem erhalten
    assert copied.is_file()
    desktop.remove_entry(entry)
    assert not copied.exists()  # unsere Kopie wird mit aufgeräumt


def test_theme_icon_name_is_kept(tmp_path):
    path = desktop.create_entry("Tool", "/bin/true", icon="utilities-terminal")
    assert "Icon=utilities-terminal\n" in path.read_text()


def test_unsupported_icon_format_rejected(tmp_path):
    jpg = write(tmp_path / "bild.jpg", "x")
    with pytest.raises(ValueError):
        desktop.install_icon(jpg, "Tool")


def test_suggest_icon_from_hidden_entry(tmp_path):
    prog = Program("foo", "1", Source.REPO)
    prog.desktop_entries = [desktop.entry_from_raw(tmp_path / "f.desktop", "f.desktop", {"Name": "Foo", "Icon": "foo-logo", "NoDisplay": "true"})]
    assert desktop.suggest_icon(prog) == "foo-logo"


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


def test_kde_userapp_entry_matches_real_path(tmp_path):
    """KDE-„userapp“-Einträge zeigen auf den echten Pfad hinter /usr/bin/… – trotzdem zuordnen."""
    real = tmp_path / "lib" / "thunderbird" / "thunderbird"
    real.parent.mkdir(parents=True)
    real.write_text("#!/bin/sh\n")
    link = tmp_path / "bin" / "thunderbird"
    link.parent.mkdir()
    link.symlink_to(real)
    apps = tmp_path / "applications"
    write(apps / "userapp-Thunderbird-BXLDV3.desktop",
          f"[Desktop Entry]\nType=Application\nName=Thunderbird\nExec={real} %u\nNoDisplay=true\n")
    tb = Program("thunderbird", "128", Source.REPO, executables=[str(link)])
    desktop.match_entries([tb], desktop.load_entries([apps]))
    assert tb.menu_status is MenuStatus.HIDDEN
    assert "Öffnen mit" in desktop.origin_note(tb.desktop_entries[0])


def test_entry_kind(tmp_path):
    from cachy_kompass.models import Kind

    visible = desktop.entry_from_raw(tmp_path / "a.desktop", "a.desktop", {"Name": "A", "Exec": "a"})
    hidden = desktop.entry_from_raw(tmp_path / "b.desktop", "b.desktop", {"Name": "B", "Exec": "b", "NoDisplay": "true"})
    git = Program("git", "2", Source.REPO, executables=["/usr/bin/git"])
    assert desktop.entry_kind(hidden, git) is Kind.COMMAND  # Art des zugehörigen Programms
    assert desktop.entry_kind(visible, None) is Kind.APP    # ohne Programm: sichtbar → App
    assert desktop.entry_kind(hidden, None) is Kind.OTHER   # ohne Programm: versteckt → Sonstiges


SYSTEM_ENTRY = """\
# Kommentar bleibt erhalten
[Desktop Entry]
Type=Application
Name=Text Editor
Name[de]=Texteditor
Exec=kate %U
DBusActivatable=true
NoDisplay=true

[Desktop Action new-window]
Name=New Window
Exec=kate --new
"""


def test_set_keys_keeps_rest_and_drops_translations():
    text = desktop.set_keys(SYSTEM_ENTRY, {"Name": "Mein Editor", "NoDisplay": None})
    raw = desktop.parse_desktop_text(text)
    assert raw["Name"] == "Mein Editor" and "Name[de]" not in raw and "NoDisplay" not in raw
    assert "# Kommentar bleibt erhalten" in text
    assert "[Desktop Action new-window]\nName=New Window" in text  # Schnellaktion unverändert
    assert desktop.set_keys("", {"Name": "x"}).startswith("[Desktop Entry]\nName=x")


def test_edit_system_entry_creates_user_copy(tmp_path):
    system = write(tmp_path / "system" / "applications" / "kde" / "kate.desktop", SYSTEM_ENTRY)
    entry = desktop.load_entries()[0]
    assert not entry.visible and not desktop.can_remove(entry)

    path = desktop.set_visible(entry, True)
    assert path == tmp_path / "applications" / "kde" / "kate.desktop"  # gleicher relativer Pfad überdeckt das Original
    assert system.read_text() == SYSTEM_ENTRY  # Systemdatei unangetastet
    entries = desktop.load_entries()
    assert len(entries) == 1 and entries[0].visible and entries[0].name == "Texteditor"
    assert desktop.overridden_system_entry(entries[0]) == system

    # Erneut bearbeiten ändert die eigene Kopie; neuer Startbefehl schaltet D-Bus-Start ab
    desktop.edit_entry(entries[0], {"Name": "Notizen", "Exec": "kate --notes"})
    edited = desktop.load_entries()[0]
    assert edited.name == "Notizen" and edited.exec == "kate --notes"
    assert "DBusActivatable" not in edited.raw

    # Ausblenden und „Entfernen“ = zurück zum Original
    desktop.set_visible(edited, False)
    hidden = desktop.load_entries()[0]
    assert not hidden.visible
    desktop.remove_entry(hidden)
    assert desktop.load_entries()[0].path == system


def test_edit_entry_copies_icon(tmp_path):
    write(tmp_path / "system" / "applications" / "x.desktop", "[Desktop Entry]\nType=Application\nName=X\nExec=x\n")
    img = write(tmp_path / "Downloads" / "logo.png", "png")
    entry = desktop.load_entries()[0]
    desktop.edit_entry(entry, {"Icon": str(img)})
    icon = desktop.load_entries()[0].icon
    assert icon.startswith(str(desktop.user_icon_dir())) and Path(icon).is_file()
