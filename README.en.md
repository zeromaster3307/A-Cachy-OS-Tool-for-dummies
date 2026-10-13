# 🧭 Cachy Software-Kompass

🇩🇪 [Deutsche Fassung](README.md)

**Which programs have I actually installed – and where did they come from?**

The Cachy Software-Kompass (German for “software compass”) is a desktop program
for [CachyOS](https://cachyos.org/). At a glance it answers:

- 📦 **What is installed?** It finds every program, no matter how it was installed.
- 🔎 **How was it installed?** Official repo, AUR, Flatpak, Snap, AppImage, pipx, cargo, npm, Homebrew or copied by hand.
- 🗂️ **Is it in the app menu?** If not, you can create an entry with two clicks.
- 🔄 **Is it updated automatically?** That is, whether the normal CachyOS system update covers it.
- ⬆️ **Is it up to date?** On request, the program checks online whether a newer version exists.
- 🧰 **Which package managers are there?** For example whether yay, Flatpak or Snap were added by following a guide.

![Main window with the program list and details](docs/screenshot-programme.png)
<sub>(Screenshot with sample data, German interface)</sub>

> **Safe:** The Software-Kompass never gets administrator rights itself.
> Reading and checking change nothing. On its own it only changes menu entries
> in your home folder. Everything else – cleaning up, “Update everything”,
> installing a package manager – it only starts when you click, after asking,
> visibly in a terminal window where you type your password yourself and
> pacman or flatpak ask once more. It never uninstalls programs; it only shows
> you the right command. Details: [What does the program change on my system?](#what-does-the-program-change-on-my-system)

---

## Contents

1. [Installation](#installation)
2. [Starting it](#starting-it)
3. [Language](#language)
4. [Using it](#using-it)
5. [Terms explained simply](#terms-explained-simply)
6. [Which sources are detected?](#which-sources-are-detected)
7. [What does the program change on my system?](#what-does-the-program-change-on-my-system)
8. [Text mode for the terminal](#text-mode-for-the-terminal)
9. [Uninstalling](#uninstalling)
10. [FAQ & problems](#faq--problems)
11. [Known limitations](#known-limitations)
12. [For developers](#for-developers)

---

## Installation

All you need is a terminal. On CachyOS with KDE it is called **Konsole** and you
find it in the app menu. Copy the following lines into it one after another and
press Enter after each:

```bash
# 1. Download the program
git clone https://github.com/zeromaster3307/A-Cachy-OS-Tool-for-dummies.git
cd A-Cachy-OS-Tool-for-dummies

# 2. Install it
./install.sh
```

The install script

1. installs the two required packages from the official repos if they are
   missing, asking for your password:
   - `pyside6` for the graphical interface
   - `pacman-contrib` for the exact update check
2. copies the program to `~/.local/share/cachy-kompass`
3. creates an app menu entry **“Cachy Software-Kompass”**.

> 💡 It also works without `git`: on the GitHub page, click the green
> **“Code” → “Download ZIP”** button, unpack the archive, open the folder in
> your file manager and choose *right-click → Open terminal here*. Then type
> `./install.sh` there.

### Updating to a new version

In the downloaded folder:

```bash
cd A-Cachy-OS-Tool-for-dummies
git pull          # download the latest version
./install.sh      # replace the installed version
```

Important: `git clone` and `git pull` only download the code. Only
`./install.sh` replaces the program that starts from the app menu. Afterwards
close the Software-Kompass once and open it again.

You do **not** have to delete the old version first; it is replaced
automatically. Menu entries you created yourself are kept.

**Which version do I have?** The version number is shown in the window title and
at the top of the “Help” tab; in the terminal, `cachy-kompass --version` shows
it. What changed between versions is listed in [CHANGELOG.md](CHANGELOG.md)
(German).

### Trying it without installing

```bash
sudo pacman -S --needed pyside6 pacman-contrib
python -m cachy_kompass
```

(run this in the downloaded folder)

---

## Starting it

- From the **app menu**: “Cachy Software-Kompass” (category *System*)
- or in the terminal: `cachy-kompass`

On start-up all programs are read in. Depending on the system this takes a few
seconds.

---

## Language

The interface is available in **German** and **English**. The Software-Kompass
follows your system language: on an English system it starts in English,
otherwise in German.

To choose the language yourself:

```bash
cachy-kompass --lang en      # English
cachy-kompass --lang de      # German
```

To always start in English from the app menu, regardless of the system
language, create the file `~/.config/environment.d/cachy-kompass.conf` with
this line and log out and back in once:

```
CACHY_KOMPASS_LANG=en
```

---

## Using it

### “Programs” tab

The main view. Every row is a program.

| Column | Meaning |
|---|---|
| **Program** | Name of the program (where possible as it appears in the app menu). **(2×)** after it means: installed twice, e.g. from the repo and additionally as a Flatpak |
| **Version** | installed version |
| **Source** | how it was installed (see [Terms](#terms-explained-simply)) |
| **Type** | 🪟 **App** (program with a window) · ⌨ **Command** (command-line program for the terminal) · 📦 **Other** (nothing to start: fonts, drivers, firmware, libraries, themes, meta packages) |
| **App menu** | ✔ visible · ◐ entry exists but is hidden · ✘ no entry |
| **Auto-update** | ✔ updated by the system update · ◐ only with the right tool · ✘ you have to update it yourself |
| **Up to date?** | only after clicking **“Check for updates”**: ✔ up to date · ⬆ newer version available |
| **Size** | disk space used. For Flatpaks only the app itself; shared runtimes come on top |
| **Installed** | when the program was installed. Exact for repo and AUR packages (from the pacman log). **“approx.”** means: date of the program files, because Flatpak, AppImage etc. keep no log (after an update this may be the update date) |
| **Description** | short description of the package |

Clicking a program shows all details on the right: where it comes from, how it
is updated, which menu entries it has and which command uninstalls it. Also:

- **Why is this installed?** For repo and AUR packages this lists the programs
  that need it. So for a dependency you can see what pulled it in.
- **What would go with it when uninstalling?** A pacman dry run shows which
  dependencies that are no longer needed would be removed as well, and how much
  space that frees. If another package still needs it, it says which one instead.
- **Installed twice:** a note if the same program also exists from another source.
- **Starting it from the terminal:** the command that starts the program in a
  terminal or via **Alt+F2** (KRunner), e.g. `vlc`. This also works when the
  menu entry is hidden. **“Copy launch command”** puts it in the clipboard.

Clicking a column header sorts the list – for example by “Up to date?”, so all
outdated programs are at the top.

**Toolbar at the top** (first row: actions and search, second row: filters):

| Element | Function |
|---|---|
| **Rescan** (F5) | searches for all programs again |
| **Check for updates** | asks online for newer versions; **nothing** is installed |
| **Update everything …** | installs all updates, see [below](#update-everything) |
| **Save list …** | saves all installed programs as a script, see [below](#saving-the-program-list) |
| **Search …** | filters **all tabs** at once: names, descriptions, names of menu entries (e.g. “Claude Code” for the program `claude`), commands and paths |
| **All sources** | only shows programs from one source, e.g. only Flatpaks |
| **Type: …** | drop-down with checkboxes (☑ Apps ☐ Commands ☐ Other), freely combinable. The button shows what is selected. The default is **apps only**, i.e. programs with a window. Ticking “Commands” also shows command-line programs, “Other” also fonts, drivers etc. The filter also applies in the “Menu entries” tab. |
| **App menu: …** | e.g. only programs **without** a menu entry |
| **Installed: …** | only programs installed in the last 7 days, 30 days or the last year. Handy for “What did I install last week while following that guide?” |
| **More filters** | drop-down with checkboxes. The number in brackets shows how many are active: |
| &nbsp;&nbsp;↳ **Only outdated** | only programs with an available update |
| &nbsp;&nbsp;↳ **Only without auto-update** | only programs whose updates you have to take care of yourself |
| &nbsp;&nbsp;↳ **Only installed twice** | only programs that exist from several sources |
| &nbsp;&nbsp;↳ **Show dependencies** | also shows libraries and automatically installed packages (often more than 1000) |

### Update everything

**“Update everything …”** shows which updates can be run on your system, each
with a checkbox:

- **System + AUR** with `paru -Syu` (without paru: `yay -Syu` or `sudo pacman -Syu`)
- **Flatpak apps** with `flatpak update`
- if present: **pipx**, **uv**, **cargo** (only with `cargo-update`) and **Homebrew**

After **“Open terminal”** the commands run one after another, visibly in a
terminal window. There you type your password and confirm the installation. If
a step fails or you cancel, the following steps are not run. What cannot be
updated automatically (e.g. AppImages) is listed in the dialog under “Not
included”.

**Restart note:** If the kernel, the graphics driver (NVIDIA, Mesa), systemd,
glibc or firmware were updated since the last boot, an orange note **“Restart
recommended”** appears at the top of the window. These updates only take effect
after a restart. So click **“Rescan”** after updating.

### Saving the program list

**“Save list …”** saves all programs you installed on purpose to a file, e.g.
`programs-2026-10-03.sh`. The file is both:

- a **readable list** of everything you installed (just open it in a text
  editor), and
- a **script** that brings everything back after reinstalling CachyOS: repo
  packages, AUR packages, Flatpaks, Snaps, pipx, uv, cargo, npm and Homebrew.

To restore your programs:

1. Before reinstalling, copy the file to a USB stick or the cloud.
2. On the new system run `bash programs-2026-10-03.sh` in a terminal.
   Important: type `bash` in front, because CachyOS uses the fish shell.
3. Every section (e.g. “Install 23 packages from the official repos?”) asks
   first. Answer `n` to skip it.

The script cannot download AppImages and programs installed by hand. They are
listed as a reminder at the end. **Settings and your own files are not
included** – they live in your home folder (e.g. `~/.config`) and belong in a
normal backup.

### Creating a menu entry

1. Select the program in the list
2. Click **“Create menu entry …”** (or double-click the row)
3. The fields are already filled in sensibly. Check them and click **“Create entry”**.

![Dialog for creating an entry](docs/screenshot-eintrag-anlegen.png)

- **Launch command:** what runs when the entry is clicked. The suggestion is
  usually right.
- **Icon:** the name of an icon from your icon theme, or your own image file
  via **“Choose image …”**. Below the field it says whether a matching icon was
  found. If not, download e.g. the logo from the program's website and choose it.
  - **SVG** or **PNG** work best. JPG, ICO, WebP etc. are converted to PNG
    automatically.
  - The image is **copied** to `~/.local/share/icons/cachy-kompass/`, so you
    can delete the downloaded file afterwards.
- **Run in a terminal window:** for programs without a window of their own
  (command-line programs such as `yt-dlp` or `htop`). Without the tick,
  clicking the entry would seem to do nothing.

### Removing a menu entry

**“Remove entry …”** (or the “Menu entries” tab) removes entries that are in
**your home folder** (`~/.local/share/applications`):

- Entries created by the Software-Kompass are removed together with their
  copied icon.
- Entries created by you or another program (e.g. by hand, with Claude, via
  Steam, Gear Lever or AppImageLauncher) can be removed too, after a clear
  warning.
- If a user entry replaces a system entry of the same name, the Software-Kompass
  tells you. After deleting it, the original system entry appears again.
- **System entries** (`/usr/share/applications` etc.) belong to packages and are
  **never** deleted. They disappear when you uninstall the program.

The program itself always stays installed; only the menu entry disappears.

### Editing, showing and hiding entries

In the **“Menu entries”** tab there are three buttons for the selected entry:

- **Edit …** changes name, description, launch command, icon, category and
  “Run in a terminal window”. Only what you actually change is changed.
- **Show / Hide** shows a hidden entry in the app menu or hides it. When hiding,
  you see the command that still starts the program in a terminal or via
  Alt+F2. The “Visible” column then says “no (by you)”. If you choose “Create
  menu entry …” in the “Programs” tab for a program that only has a hidden
  entry, showing it is offered as well.
- **Remove … / Restore original …** (see above).

**System entries always stay unchanged.** Instead, the Software-Kompass saves
your version under the same name in your home folder, where it replaces the
system entry in the app menu. **“Restore original …”** deletes your version and
the original entry applies again. Note: if a later update changes the system
entry, your version still applies until you remove it.

### “Menu entries” tab

Lists **all** menu entries on the system and shows which program they belong
to. The “Launch command” column shows how you can also start the program in a
terminal or via Alt+F2 (**“Copy launch command”** copies it). If it says
**“Program missing”**, the entry points to a program that no longer exists –
probably a leftover from an uninstall.

There is also a **“Type”** column (the type of the program it belongs to), and
the same “Type” filter as in the program list applies.

### “Package managers” tab

![Overview of package managers](docs/screenshot-paketverwaltungen.png)

Shows which package managers, app stores and update tools are present and how
many programs were installed through each. For example, you can see whether you
once installed Snap or Homebrew for some guide.

Every tool has a **rating** with a reason:

| Rating | Meaning | Examples |
|---|---|---|
| ✔ **recommended** | fits CachyOS well, low risk | Flatpak, paru, CachyOS Package Installer, cachy-update |
| ◐ **if needed** | useful if you need it, otherwise unnecessary | pipx, uv, Gear Lever, Topgrade, Discover, Distrobox |
| ✘ **not recommended** | redundant, bypasses the system or unusual on Arch | Snap, Homebrew, Nix, pip, yay (next to paru), Pamac |

**Installing:** If a “recommended” or “if needed” tool is missing, you can add it
with **“Install …”**. The rules:

- It is installed **only from the official package repositories** (CachyOS/Arch).
  The Software-Kompass first checks with `pacman -Si` that the package is really
  available there. Only exception: Gear Lever is taken from Flathub if it is not
  in the repos and Flatpak is already present.
- **Nothing from the AUR, no scripts from the internet.**
- The command runs **visibly in a terminal window** (e.g. Konsole). You type your
  password there yourself, and pacman asks again before installing. The
  Software-Kompass never gets administrator rights.
- “Not recommended” tools get **no** install button, only the reason and a
  better alternative.
- **Removing** deliberately has no button. Removing a package manager also
  removes every program installed through it. The details show the number of
  affected programs and the command.

### “Clean up” tab

![Clean up tab](docs/screenshot-aufraeumen.png)
<sub>(Screenshot with sample data, German interface)</sub>

Clicking **“Check now”** looks for things that take up space for no reason or
are broken. Checking itself changes nothing.

| Finding | What is it? | Cleaning up |
|---|---|---|
| **Orphaned packages** | dependencies no program needs any more | `sudo pacman -Rns …`, pacman shows the list first |
| **Package cache** | old package versions in `/var/cache/pacman/pkg`, often several GB | `paccache` keeps the 2 newest versions of each package (as a way back in an emergency) |
| **AUR build folders** | leftovers from building AUR packages (paru/yay) in `~/.cache` | delete the folders; they are recreated on the next update |
| **Unused Flatpak runtimes** | runtimes no app needs any more | `flatpak uninstall --unused`, Flatpak shows the list first |
| **Broken menu entries** | entries whose program is missing | entries in your home folder are removed directly |
| **Installed twice** | the same program from several sources, e.g. repo and Flatpak (detected by name) | **no button**, only an explanation and the removal commands – you decide which version stays |
| **No longer in the AUR** | AUR packages that are no longer listed there and get no more updates | **no button**, only an explanation and the command – you decide |

The total space you could free is shown at the top. **“Clean up …”** opens a
terminal window with the commands shown, after asking. There you see everything
and confirm yourself. Afterwards click “Check now” again.

### “Help” tab

A short version of this guide inside the program.

---

## Terms explained simply

| Term | Explanation |
|---|---|
| **Package** | A program (or part of one) in a form that a package manager can install, update and remove. |
| **pacman** | The package manager of CachyOS and Arch Linux. It handles the official packages. |
| **Repo** (repository) | An online store of ready-made packages. CachyOS has its own repos (`cachyos`, `cachyos-v3` …, optimized for your processor) and also uses those of Arch Linux (`core`, `extra`, `multilib`). |
| **AUR** | The *Arch User Repository*: a huge collection of community build recipes. Not officially reviewed. Used with an **AUR helper** such as `paru` (included with CachyOS) or `yay`. |
| **Chaotic-AUR** | An additional, unofficial repo with prebuilt AUR packages. Often set up by following guides. |
| **Flatpak / Flathub** | A system for sandboxed apps, independent of the Linux distribution. Flathub is the largest Flatpak “store”. |
| **Snap** | Similar to Flatpak, comes from Ubuntu. Unusual on CachyOS. |
| **AppImage** | A program in a single file that you download and start directly, without installing. |
| **pipx / uv** | Tools for installing Python programs cleanly separated from the system. |
| **cargo** | The tool of the Rust programming language. Can build and install programs from source. |
| **npm** | Package manager for JavaScript/Node.js. |
| **Homebrew** | Package manager from the macOS world, also available for Linux. |
| **Dependency** | A package that is needed not by you but by another program, e.g. a library. Installed automatically. |
| **.desktop file** | A small text file describing a menu entry (name, icon, launch command). System-wide ones are in `/usr/share/applications`, your own in `~/.local/share/applications`. |
| **System update** | On CachyOS: `sudo pacman -Syu` updates all repo packages, `paru` also all AUR packages. Flatpaks are updated with `flatpak update`. |

---

## Which sources are detected?

| Source | How detected | Auto-update with the system update? | How “Up to date?” is checked |
|---|---|---|---|
| **Official repo** (CachyOS, Arch, extra repos such as Chaotic-AUR) | `pacman -Qi`, `pacman -Sl` | ✔ yes (`pacman -Syu`, `paru`) | `checkupdates` (downloads a fresh package list into a temporary folder without changing the system) |
| **AUR** | `pacman -Qm` (packages that are in no repo) | ◐ only with an AUR helper (`paru`, `yay`), not with a plain `pacman -Syu` | query of the AUR web API |
| **Flatpak** | `flatpak list --app` | ◐ with `flatpak update` or Discover/GNOME Software | `flatpak remote-ls --updates` |
| **Snap** | `snap list` | ✔ yes, snapd updates by itself | `snap refresh --list` |
| **AppImage** | search for `*.AppImage` in `~/Applications`, `~/AppImages`, `~/Downloads`, `~/.local/bin`, `/opt` and others | ✘ no | not possible (no central version list) |
| **pipx** | `pipx list --json` | ✘ no (`pipx upgrade-all`) | query of PyPI |
| **uv tool** | `uv tool list` | ✘ no (`uv tool upgrade --all`) | query of PyPI |
| **cargo** | `cargo install --list` | ✘ no | query of crates.io |
| **npm** | `npm ls -g` (without those managed by pacman) | ✘ no (`npm update -g`) | `npm outdated -g` |
| **Homebrew** | `brew list --versions` | ✘ no (`brew upgrade`) | `brew outdated` |
| **Manual** | programs in `~/.local/bin`, `~/bin`, `~/go/bin`, `/usr/local/bin` and folders in `/opt` that belong to no package manager | ✘ no | not possible |

Menu entries are read from all the usual folders (including Flatpak and Snap
entries) and matched to programs like this:

1. **Certain:** the file belongs to the package according to pacman, or the entry
   carries the Flatpak ID or Snap name.
2. **Via the launch command:** the entry starts a program file that belongs to a
   program (e.g. `~/.cargo/bin/rg` → ripgrep). Terminals and shells are looked
   through: an entry with `konsole -e claude` or `sh -c "cd ~/Projects && claude"`
   belongs to `claude`, not to Konsole.

---

## What does the program change on my system?

| Action | Changes anything? |
|---|---|
| Reading programs | No, read-only |
| Check for updates | No. Only version numbers are fetched from the internet. `checkupdates` works in a temporary folder and does not touch the system's package database. |
| Create menu entry | Creates **one** file `~/.local/share/applications/cachy-kompass-<name>.desktop`, plus a copy of your own image in `~/.local/share/icons/cachy-kompass/` |
| Remove entry | Only deletes entries from your home folder, after asking. Entries created by others get an extra warning. System entries are never touched. |
| Edit, show/hide entry | Changes entries in your home folder. For system entries a modified copy is created there; the original stays unchanged. |
| Update everything | Only after asking, visibly in a terminal window where you type your password and confirm the installation yourself |
| Save list | Saves a file where you choose. Changes nothing else. |
| Showing details | “What would go with it when uninstalling?” uses `pacman -Rsp`, a pure dry run without administrator rights |
| Clean up | Checking changes nothing. Cleaning up only happens after asking, visibly in a terminal window; pacman, paccache and flatpak ask again there. The Software-Kompass itself only deletes broken menu entries in your home folder. |
| Installing a package manager | Only after asking, only from the official package repositories, visibly in a terminal window where you type your password yourself |
| Uninstalling programs | **The Software-Kompass does not do this.** It only shows you the right command, which you can copy into a terminal yourself. |

The update check contacts the following addresses (only when you click “Check
for updates”): the CachyOS/Arch package mirrors (via `checkupdates`),
`aur.archlinux.org`, Flathub, the Snap Store, `pypi.org`, `crates.io`, the npm
registry and Homebrew.

---

## Text mode for the terminal

Everything is also available without the window:

```bash
cachy-kompass --cli                 # table of all programs
cachy-kompass --cli --updates       # … with update check
cachy-kompass --cli --all           # … including dependencies/libraries
cachy-kompass --cli --installers    # … plus the list of package managers
cachy-kompass --json > list.json    # machine-readable, e.g. as a backup of your program list
cachy-kompass --lang en --cli       # in English, whatever the system language
cachy-kompass --help                # all options
```

---

## Uninstalling

In the downloaded folder:

```bash
./uninstall.sh
```

The script asks whether the menu entries you created (and their icons) should
be deleted too. The packages `pyside6` and `pacman-contrib` stay installed; if
you no longer need them: `sudo pacman -Rns pyside6 pacman-contrib`.

---

## FAQ & problems

**Why does a program have no menu entry?**
Many programs deliberately have none: command-line programs (e.g. `git`,
`htop`), background services, drivers. A custom entry is only worth it when a
program with a window is missing.

**Why does an AUR package say “unknown”?**
Either it is not (or no longer) in the AUR (maybe self-built or orphaned), or it
is a development version (`-git`) whose version number in the AUR means nothing.

**The update check for repo packages is inaccurate.**
Install `pacman-contrib` (`sudo pacman -S pacman-contrib`). Without the
`checkupdates` program the Software-Kompass only compares with the most recently
downloaded package list.

**A newly created entry does not appear in the app menu.**
Usually it is enough to close and reopen the app menu. On KDE,
`kbuildsycoca6` in a terminal or logging out and back in helps if needed.

**“The graphical interface needs PySide6”**
Run `sudo pacman -S pyside6`.

**How do I bring everything up to date at once?**
On CachyOS the easiest way is in a terminal:
```bash
paru              # repo and AUR packages
flatpak update    # Flatpaks
```
For pipx, cargo, npm etc. the matching command is shown in the details. If you
like it convenient, install `topgrade`, which updates everything with one
command.

**I found a bug.**
Start the program in a terminal with `cachy-kompass -v` to get detailed
messages, and open an issue on GitHub.

---

## Known limitations

- Designed for **CachyOS** (works just as well on Arch Linux and Arch-based
  systems such as EndeavourOS).
- **Nix** and **Distrobox** programs are only detected as “present”, not listed
  individually.
- For **AppImages** and **manually** installed programs there is no central
  version list, so their up-to-dateness cannot be checked. For AppImages the
  version is guessed from the file name.
- Matching menu entries via the launch command is a good estimate but not
  perfect in every special case.
- “Up to date” refers to the time of the check.
- **Duplicates** are detected by name. Very rarely, two programs with the same
  name are different things. That is why there is no clean-up button for them.
- The **installation date** of repo and AUR packages comes from
  `/var/log/pacman.log`. If the log was deleted, the date is missing.
- The screenshots show the German interface.

---

## For developers

The developer documentation is in German: [docs/ENTWICKLUNG.md](docs/ENTWICKLUNG.md).
In short:

```bash
pip install pytest ruff     # or: sudo pacman -S python-pytest ruff
pytest                      # tests (also run without CachyOS)
ruff check .                # code style
python -m cachy_kompass     # start
python tools/i18n.py check  # are all texts translated?
```

German is the source language in the code; texts are marked with `_("…")` and
the English translation lives in `cachy_kompass/locale/en.po`.

## License

Copyright © 2026 zeromaster3307 and contributors

The Cachy Software-Kompass is free software under the
**GNU General Public License, version 3 or later** (GPL-3.0-or-later).
The full license text is in the [LICENSE](LICENSE) file.

In short (not legally binding):

- You may **use, share and modify** the program, also commercially.
- If you **share a modified version**, it must also be under the GPL, and the
  source code must be included or made available.
- There is **no warranty**: use at your own risk.
