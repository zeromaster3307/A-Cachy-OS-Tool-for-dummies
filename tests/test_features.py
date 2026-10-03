"""Tests für Installationsdatum, Neustart-Hinweis, Größen, Doppelte, „Alles aktualisieren“ und Sicherung."""

import subprocess
from datetime import datetime, timedelta, timezone
from shutil import which

import pytest

from cachy_kompass import backup, cleanup, duplicates, history, sizes, update_all
from cachy_kompass.models import Program, Source
from cachy_kompass.sources import pacman

LOG = """\
[2019-03-01 12:00] [ALPM] installed oldtool (1.0-1)
[2024-10-01T10:00:00+0200] [ALPM] installed firefox (131.0-1)
[2024-10-01T10:00:01+0200] [ALPM-SCRIPTLET] irgendwas
[2024-10-05T18:12:44+0200] [ALPM] upgraded firefox (131.0-1 -> 131.0.2-1)
[2024-10-06T09:00:00+0200] [ALPM] upgraded linux-cachyos (6.11.1-1 -> 6.11.2-1)
[2024-10-06T09:00:00+0200] [ALPM] upgraded linux-cachyos-headers (6.11.1-1 -> 6.11.2-1)
[2024-10-06T09:00:01+0200] [ALPM] upgraded nvidia-utils (560-1 -> 565-1)
[2024-10-06T09:00:02+0200] [ALPM] removed vlc (3.0.21-1)
[2024-10-07T09:00:00+0200] [ALPM] installed vlc (3.0.21-2)
"""


def test_parse_log_and_install_dates():
    events = history.parse_log(LOG)
    assert len(events) == 8  # Skript-Zeile wird übersprungen
    dates = history.install_dates(events)
    assert dates["firefox"] == datetime(2024, 10, 1, 10, 0, tzinfo=timezone(timedelta(hours=2)))  # Update zählt nicht
    assert dates["vlc"].day == 7  # neu installiert nach dem Entfernen
    assert dates["oldtool"].year == 2019 and dates["oldtool"].tzinfo is not None  # altes Format


def test_fill_install_dates(tmp_path):
    events = history.parse_log(LOG)
    ff = Program("firefox", "1", Source.REPO)
    f = tmp_path / "Obsidian.AppImage"
    f.write_text("x")
    ai = Program("Obsidian", "1", Source.APPIMAGE, install_path=str(f))
    history.fill_install_dates([ff, ai], events)
    assert ff.installed_at.day == 1 and not ff.installed_approx
    assert ai.installed_at is not None and ai.installed_approx


def test_reboot_check(tmp_path):
    events = history.parse_log(LOG)
    booted = datetime(2024, 10, 6, 0, 0, tzinfo=timezone.utc)
    modules = tmp_path / "modules"
    (modules / "6.11.2-1-cachyos").mkdir(parents=True)
    info = history.check_reboot(events, booted, "6.11.1-1-cachyos", modules)
    assert info.kernel_replaced and info.needed
    assert info.packages == ["linux-cachyos", "nvidia-utils"]  # Header zählen nicht, vlc auch nicht
    assert "Kernel" in info.message()
    fresh = history.check_reboot(events, datetime(2024, 10, 8, tzinfo=timezone.utc), "6.11.2-1-cachyos", modules)
    assert not fresh.needed and fresh.message() == ""


def test_needs_reboot_for():
    assert history.needs_reboot_for("linux")
    assert history.needs_reboot_for("systemd")
    assert not history.needs_reboot_for("linux-api-headers")
    assert not history.needs_reboot_for("firefox")


def test_sizes(tmp_path):
    assert sizes.parse_decimal_size("52.4 MB") == 52_400_000
    assert sizes.parse_decimal_size("1,2\xa0GB") == 1_200_000_000
    assert sizes.parse_decimal_size("900 bytes") == 900
    assert sizes.parse_decimal_size("?") == 0
    folder = tmp_path / "opt" / "tool"
    folder.mkdir(parents=True)
    (folder / "a").write_bytes(b"x" * 1000)
    (folder / "b").write_bytes(b"x" * 500)
    manual = Program("tool", "?", Source.MANUAL, install_path=str(folder))
    repo = Program("firefox", "1", Source.REPO, size_bytes=42)
    sizes.fill_sizes([manual, repo])
    assert manual.size_bytes == 1500 and repo.size_bytes == 42


def test_duplicates():
    ff_repo = Program("firefox", "131", Source.REPO)
    ff_flat = Program("org.mozilla.firefox", "131", Source.FLATPAK, display_name="Firefox")
    ytdlp = Program("yt-dlp", "1", Source.REPO)
    ytdlp_pipx = Program("yt-dlp", "2", Source.PIPX)
    code = Program("visual-studio-code-bin", "1", Source.AUR, display_name="Visual Studio Code")
    code_flat = Program("com.visualstudio.code", "1", Source.FLATPAK, display_name="Visual Studio Code")
    alone = Program("gimp", "2", Source.REPO)
    dep = Program("org.gimp.GIMP", "2", Source.FLATPAK, explicit=False)
    groups = duplicates.find_duplicates([ff_repo, ff_flat, ytdlp, ytdlp_pipx, code, code_flat, alone, dep])
    assert len(groups) == 3
    assert ff_repo.duplicates == [ff_flat] and ff_flat.duplicates == [ff_repo]
    assert ytdlp_pipx.duplicates == [ytdlp]
    assert code.duplicates == [code_flat]
    assert alone.duplicates == []  # Abhängigkeiten zählen nicht
    item = cleanup.check_duplicates(groups)
    assert item.found and item.summary == "3 Programme" and "flatpak uninstall" in item.details[0]


def test_update_all_plan():
    progs = [Program("a", "1", Source.REPO), Program("b", "1", Source.AUR), Program("c", "1", Source.FLATPAK),
             Program("d", "1", Source.PIPX), Program("e", "1", Source.APPIMAGE)]
    have = {"paru", "pacman", "flatpak"}
    steps = update_all.plan(progs, which=lambda c: f"/usr/bin/{c}" if c in have else None)
    assert [s.command for s in steps] == [["paru", "-Syu"], ["flatpak", "update"]]  # pipx fehlt → kein Schritt
    only_pacman = update_all.plan(progs, which=lambda c: "/usr/bin/pacman" if c == "pacman" else None)
    assert only_pacman[0].command == ["sudo", "pacman", "-Syu"] and "AUR" in only_pacman[0].explanation
    notes = update_all.not_covered(progs, steps)
    assert any("AppImage" in n for n in notes)


def test_backup_script():
    progs = [
        Program("firefox", "1", Source.REPO), Program("glibc", "1", Source.REPO, explicit=False),
        Program("spotify", "1", Source.AUR),
        Program("org.gimp.GIMP", "1", Source.FLATPAK, installation="system"),
        Program("com.spotify.Client", "1", Source.FLATPAK, installation="user"),
        Program("yt-dlp", "1", Source.PIPX),
        Program("mytool", "1", Source.CARGO, install_path="https://github.com/me/mytool"),
        Program("Obsidian", "1", Source.APPIMAGE, install_path="/home/u/Apps/Obsidian.AppImage"),
    ]
    script = backup.build_script(progs, datetime(2026, 10, 3, 12, 0), "cachy")
    assert "sudo pacman -S --needed" in script and "firefox" in script and "glibc" not in script
    assert "paru -S --needed" in script and "spotify" in script
    assert "flatpak install --system flathub" in script and "flatpak install --user flathub" in script
    assert "pipx install yt-dlp" in script
    assert "cargo install mytool" not in script and "#   • mytool" in script
    assert "Obsidian" in script
    if which("bash"):
        subprocess.run(["bash", "-n"], input=script, text=True, check=True)  # Syntax gültig
    assert backup.default_filename(datetime(2026, 10, 3)) == "programme-2026-10-03.sh"


def test_pacman_removal_helpers():
    assert pacman.name_list("None") == []
    assert pacman.name_list("firefox  vlc") == ["firefox", "vlc"]
    assert pacman.parse_removal_preview("firefox\nlibfoo\n") == ["firefox", "libfoo"]
    err = (
        "checking dependencies...\n"
        "error: failed to prepare transaction (could not satisfy dependencies)\n"
        ":: removing gtk3 breaks dependency 'gtk3' required by firefox\n"
        ":: removing gtk3 breaks dependency 'gtk3>=3.24' required by gimp\n"
    )
    assert pacman.parse_removal_error(err) == "Wird noch gebraucht von: firefox, gimp"


@pytest.mark.parametrize("qi_field", ["Required By", "Optional For"])
def test_parse_qi_dependency_fields(qi_field):
    text = f"Name            : gtk3\nVersion         : 1\n{qi_field:<16}: firefox  gimp\n"
    assert pacman.name_list(pacman.parse_qi(text)[0][qi_field]) == ["firefox", "gimp"]
