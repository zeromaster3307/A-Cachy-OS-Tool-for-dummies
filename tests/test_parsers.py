"""Tests für das Auswerten der Ausgaben der verschiedenen Paketverwaltungen.

Die Beispieltexte entsprechen dem, was die Programme unter CachyOS ausgeben.
So lassen sich die Tests auch auf Rechnern ohne pacman/flatpak/… ausführen.
"""

from cachy_kompass.models import Program, Source, UpdateStatus
from cachy_kompass.sources import devtools, flatpak, pacman, python_tools, snap
from cachy_kompass.sources.base import compare_result
from cachy_kompass.sources.files import split_appimage_name
from cachy_kompass.util import _simple_vercmp, parse_pacman_owners

PACMAN_QI = """\
Name            : firefox
Version         : 131.0-1.1
Description     : Fast, Private & Safe Web Browser
Architecture    : x86_64_v3
URL             : https://www.mozilla.org/firefox/
Licenses        : MPL-2.0
Optional Deps   : networkmanager: Location detection via available WiFi networks
                  libnotify: Notification integration [installed]
Install Date    : Tue 01 Oct 2024 10:00:00 AM CEST
Install Reason  : Explicitly installed
Validated By    : Signature

Name            : glibc
Version         : 2.40+r16-1.1
Description     : GNU C Library
Install Reason  : Installed as a dependency for another package

Name            : spotify
Version         : 1:1.2.45.454-1
Description     : A proprietary music streaming service
Install Reason  : Explicitly installed
"""

PACMAN_SL = """\
cachyos-v3 firefox 131.0-1.1 [installed]
cachyos-core-v3 glibc 2.40+r16-1.1 [installed]
core glibc 2.40+r16-1 [installed: 2.40+r16-1.1]
extra firefox 131.0-1
extra vlc 3.0.21-3
"""

PACMAN_QL = """\
firefox /usr/
firefox /usr/bin/
firefox /usr/bin/firefox
firefox /usr/lib/firefox/firefox
firefox /usr/share/applications/firefox.desktop
glibc /usr/bin/ldd
spotify /usr/bin/spotify
spotify /usr/share/applications/spotify.desktop
"""


def test_parse_qi():
    pkgs = pacman.parse_qi(PACMAN_QI)
    assert [p["Name"] for p in pkgs] == ["firefox", "glibc", "spotify"]
    assert pkgs[0]["Install Reason"] == "Explicitly installed"
    assert "libnotify" in pkgs[0]["Optional Deps"]  # Fortsetzungszeile
    assert pkgs[1]["Install Reason"].startswith("Installed as a dependency")
    assert pkgs[2]["Version"] == "1:1.2.45.454-1"


def test_parse_sl_first_repo_wins():
    repos = pacman.parse_sl(PACMAN_SL)
    assert repos["firefox"] == ("cachyos-v3", "131.0-1.1")
    assert repos["glibc"][0] == "cachyos-core-v3"
    assert repos["vlc"] == ("extra", "3.0.21-3")


def test_parse_ql():
    exes, desktops = pacman.parse_ql(PACMAN_QL)
    assert exes["firefox"] == ["/usr/bin/firefox"]
    assert desktops["spotify"] == ["/usr/share/applications/spotify.desktop"]
    assert "glibc" not in desktops


def test_parse_checkupdates():
    out = "firefox 131.0-1.1 -> 131.0.2-1.1\nmesa 1:24.2.3-1 -> 1:24.2.4-1\n"
    assert pacman.parse_checkupdates(out) == {"firefox": "131.0.2-1.1", "mesa": "1:24.2.4-1"}


def test_describe_repo():
    assert "x86-64-v3" in pacman.describe_repo("cachyos-v3")
    assert "Zen" in pacman.describe_repo("cachyos-znver4")
    assert "Arch" in pacman.describe_repo("extra")
    assert "Chaotic" in pacman.describe_repo("chaotic-aur")
    assert "nachträglich" in pacman.describe_repo("meinrepo")


def test_flatpak_list():
    out = (
        "org.mozilla.Thunderbird\tThunderbird\t128.3.0esr\tstable\tflathub\tsystem\n"
        "com.spotify.Client\tSpotify\t\tstable\tflathub\tuser\n"
    )
    rows = flatpak.parse_list(out)
    assert rows[0]["application"] == "org.mozilla.Thunderbird"
    assert rows[1]["version"] == "" and rows[1]["installation"] == "user"


def test_flatpak_updates():
    assert flatpak.parse_updates("org.gimp.GIMP\t2.10.38\n") == {"org.gimp.GIMP": "2.10.38"}


def test_snap_list():
    out = """\
Name               Version          Rev    Tracking         Publisher   Notes
core22             20240823         1621   latest/stable    canonical✓  base
firefox            131.0-1          4955   latest/stable    mozilla✓    -
snapd              2.65.3           23258  latest/stable    canonical✓  snapd
gtk-common-themes  0.1-81-g442e511  1535   latest/stable/…  canonical✓  -
"""
    rows = snap.parse_list(out)
    runtime = {r["name"]: snap.is_runtime(r) for r in rows}
    assert runtime == {"core22": True, "firefox": False, "snapd": True, "gtk-common-themes": True}


def test_snap_refresh_list():
    out = "Name     Version  Rev   Size   Publisher   Notes\nfirefox  132.0    5000  280MB  mozilla✓    -\n"
    assert snap.parse_refresh_list(out) == {"firefox": "132.0"}


def test_pipx_json():
    out = '{"venvs": {"yt-dlp": {"metadata": {"main_package": {"package": "yt-dlp", "package_version": "2024.10.7", "apps": ["yt-dlp"]}}}}}'
    assert python_tools.parse_pipx_json(out) == [{"name": "yt-dlp", "version": "2024.10.7", "apps": ["yt-dlp"]}]
    assert python_tools.parse_pipx_json("kein json") == []


def test_uv_list():
    out = "black v24.8.0\n- black\n- blackd\nruff v0.6.9\n- ruff\n"
    rows = python_tools.parse_uv_list(out)
    assert rows[0] == {"name": "black", "version": "24.8.0", "apps": ["black", "blackd"]}
    assert rows[1]["name"] == "ruff"


def test_cargo_list():
    out = """\
bat v0.24.0:
    bat
mytool v0.1.0 (https://github.com/me/mytool#a1b2c3d):
    mytool
    mytool-helper
"""
    rows = devtools.parse_cargo_list(out)
    assert rows[0] == {"name": "bat", "version": "0.24.0", "from": "", "bins": ["bat"]}
    assert rows[1]["from"].startswith("https://github.com")
    assert rows[1]["bins"] == ["mytool", "mytool-helper"]


def test_npm():
    ls = '{"dependencies": {"npm": {"version": "10.9.0"}, "typescript": {"version": "5.6.2"}}}'
    assert devtools.parse_npm_ls(ls) == {"npm": "10.9.0", "typescript": "5.6.2"}
    outdated = '{"typescript": {"current": "5.6.2", "wanted": "5.6.3", "latest": "5.6.3"}}'
    assert devtools.parse_npm_outdated(outdated) == {"typescript": "5.6.3"}
    assert devtools.parse_npm_outdated("") == {}


def test_brew():
    assert devtools.parse_brew_versions("gh 2.58.0\nnode 22.9.0 22.8.0\n") == {"gh": "2.58.0", "node": "22.8.0"}
    out = '{"formulae": [{"name": "gh", "installed_versions": ["2.58.0"], "current_version": "2.59.0"}], "casks": []}'
    assert devtools.parse_brew_outdated(out) == {"gh": "2.59.0"}


def test_appimage_names():
    assert split_appimage_name("Obsidian-1.6.7.AppImage") == ("Obsidian", "1.6.7")
    assert split_appimage_name("LM-Studio-0.3.4-x86_64.AppImage") == ("LM-Studio", "0.3.4")
    assert split_appimage_name("cursor.appimage") == ("cursor", "")
    assert split_appimage_name("balenaEtcher-1.19.21-x64.AppImage") == ("balenaEtcher", "1.19.21")


def test_pacman_owners():
    out = "/usr/bin/foo is owned by foo 1.0-1\n/opt/bar/ is owned by bar-bin 2.0-1\nerror: No package owns /opt/x\n"
    assert parse_pacman_owners(out) == {"/usr/bin/foo": "foo", "/opt/bar": "bar-bin"}


def test_versions():
    assert _simple_vercmp("1.10", "1.9") > 0
    assert _simple_vercmp("2.0", "2.0") == 0
    assert compare_result("1.0", "1.0").status is UpdateStatus.CURRENT
    assert compare_result("v1.0", "1.1").status is UpdateStatus.OUTDATED
    assert compare_result("1.0", None).status is UpdateStatus.UNKNOWN


def test_uninstall_command():
    assert Program("firefox", "1", Source.REPO).uninstall_command() == "sudo pacman -Rns firefox"
    fp = Program("org.gimp.GIMP", "1", Source.FLATPAK, installation="user")
    assert fp.uninstall_command() == "flatpak uninstall --user org.gimp.GIMP"
    ai = Program("Obsidian", "1", Source.APPIMAGE, install_path="/home/u/Apps/Obsidian.AppImage")
    assert ai.uninstall_command() == "rm /home/u/Apps/Obsidian.AppImage"
