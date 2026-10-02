# 🧭 Cachy Software-Kompass

**Welche Programme habe ich eigentlich installiert – und woher kommen die?**

Der Cachy Software-Kompass ist ein Programm mit grafischer Oberfläche für
[CachyOS](https://cachyos.org/). Es beantwortet auf einen Blick:

- 📦 **Was ist installiert?** Es findet alle Programme, egal auf welchem Weg sie installiert wurden.
- 🔎 **Wie wurde es installiert?** Ob offizielles Repo, AUR, Flatpak, Snap, AppImage, pipx, cargo, npm, Homebrew oder von Hand kopiert.
- 🗂️ **Ist es im Startmenü?** Falls nicht, legst du mit zwei Klicks einen Eintrag an.
- 🔄 **Wird es automatisch aktualisiert?** Also ob das normale CachyOS-Systemupdate das Programm mit erfasst.
- ⬆️ **Ist es aktuell?** Das Programm prüft auf Wunsch im Internet, ob es eine neuere Version gibt.
- 🧰 **Welche Paketverwaltungen gibt es?** Zum Beispiel ob yay, Flatpak oder Snap durch eine Anleitung nachinstalliert wurden.

![Hauptfenster mit Programmliste und Detailansicht](docs/screenshot-programme.png)
<sub>(Screenshot mit Beispieldaten)</sub>

> **Sicher:** Der Software-Kompass schaut nur nach. Er installiert, aktualisiert
> und löscht **keine** Programme. Das Einzige, was er anlegen kann, sind
> Startmenü-Einträge in deinem eigenen Benutzerordner, und nur genau diese kann
> er auch wieder entfernen.

---

## Inhalt

1. [Installation](#installation)
2. [Starten](#starten)
3. [Bedienung](#bedienung)
4. [Begriffe einfach erklärt](#begriffe-einfach-erklärt)
5. [Welche Quellen werden erkannt?](#welche-quellen-werden-erkannt)
6. [Was ändert das Programm an meinem System?](#was-ändert-das-programm-an-meinem-system)
7. [Textmodus für das Terminal](#textmodus-für-das-terminal)
8. [Deinstallation](#deinstallation)
9. [Häufige Fragen & Probleme](#häufige-fragen--probleme)
10. [Bekannte Grenzen](#bekannte-grenzen)
11. [Für Entwickler](#für-entwickler)

---

## Installation

Du brauchst nur ein Terminal. Unter CachyOS mit KDE heißt es **Konsole**, du
findest es im Startmenü. Kopiere die folgenden Zeilen nacheinander hinein und
drücke jeweils Enter:

```bash
# 1. Das Programm herunterladen
git clone https://github.com/zeromaster3307/A-Cachy-OS-Tool-for-dummies.git
cd A-Cachy-OS-Tool-for-dummies

# 2. Installieren
./install.sh
```

Das Installationsskript

1. installiert, falls sie fehlen, die zwei benötigten Pakete aus den offiziellen
   Repos und fragt dafür nach deinem Passwort:
   - `pyside6` für die grafische Oberfläche
   - `pacman-contrib` für die genaue Update-Prüfung
2. kopiert das Programm nach `~/.local/share/cachy-kompass`
3. legt einen Startmenü-Eintrag **„Cachy Software-Kompass“** an.

> 💡 Ohne `git` geht es auch: Lade auf der GitHub-Seite über den grünen Knopf
> **„Code“ → „Download ZIP“** das Archiv herunter, entpacke es, öffne den Ordner
> im Dateimanager und wähle *Rechtsklick → Terminal hier öffnen*. Dort dann
> `./install.sh` eingeben.

### Ohne Installation ausprobieren

```bash
sudo pacman -S --needed pyside6 pacman-contrib
python -m cachy_kompass
```

(im heruntergeladenen Ordner ausführen)

---

## Starten

- Über das **Startmenü**: „Cachy Software-Kompass“ (Kategorie *System*)
- oder im Terminal: `cachy-kompass`

Beim Start werden alle Programme eingelesen. Das dauert je nach System ein paar
Sekunden.

---

## Bedienung

### Reiter „Programme“

Die Hauptansicht. Jede Zeile ist ein Programm.

| Spalte | Bedeutung |
|---|---|
| **Programm** | Name des Programms (wenn möglich so, wie er im Startmenü steht) |
| **Version** | installierte Version |
| **Quelle** | auf welchem Weg es installiert wurde (siehe [Begriffe](#begriffe-einfach-erklärt)) |
| **Startmenü** | ✔ sichtbar · ◐ Eintrag vorhanden, aber ausgeblendet · ✘ kein Eintrag |
| **Auto-Update** | ✔ wird beim Systemupdate mit aktualisiert · ◐ nur mit dem richtigen Werkzeug · ✘ musst du selbst aktualisieren |
| **Aktuell?** | erst nach Klick auf **„Nach Updates suchen“**: ✔ aktuell · ⬆ neuere Version verfügbar |
| **Beschreibung** | Kurzbeschreibung des Pakets |

Ein Klick auf ein Programm zeigt rechts alle Details: woher es kommt, wie es
aktualisiert wird, welche Startmenü-Einträge es hat und mit welchem Befehl man
es wieder deinstalliert.

Ein Klick auf eine Spaltenüberschrift sortiert die Liste, zum Beispiel nach
„Aktuell?“, dann stehen alle veralteten Programme oben.

**Werkzeugleiste oben:**

| Element | Funktion |
|---|---|
| **Neu einlesen** (F5) | sucht alle Programme erneut |
| **Nach Updates suchen** | fragt im Internet nach neueren Versionen; dabei wird **nichts** installiert |
| **Suchen …** | filtert nach Name oder Beschreibung |
| **Alle Quellen** | zeigt nur Programme aus einer bestimmten Quelle, z. B. nur Flatpaks |
| **Startmenü: …** | zeigt z. B. nur Programme **ohne** Startmenü-Eintrag |
| **Nur veraltete** | zeigt nur Programme mit verfügbarem Update |
| **Nur ohne Auto-Update** | zeigt nur Programme, um deren Updates du dich selbst kümmern musst |
| **Abhängigkeiten zeigen** | blendet auch Bibliotheken und automatisch mitinstallierte Pakete ein (das sind oft über 1000) |

### Einen Startmenü-Eintrag anlegen

1. Programm in der Liste auswählen
2. **„Startmenü-Eintrag anlegen …“** klicken (oder Doppelklick auf die Zeile)
3. Die Felder sind schon sinnvoll vorausgefüllt. Prüfen und auf **„Eintrag anlegen“** klicken.

![Dialog zum Anlegen eines Eintrags](docs/screenshot-eintrag-anlegen.png)

- **Startbefehl:** Was beim Klick auf den Eintrag ausgeführt wird. Normalerweise
  passt der Vorschlag.
- **Symbol:** Der Name eines Symbols aus deinem Symbol-Design oder eine eigene
  Bilddatei über „Bild wählen …“.
- **In einem Terminalfenster starten:** Für Programme ohne eigenes Fenster
  (Kommandozeilenprogramme wie `yt-dlp` oder `htop`). Ohne Häkchen würde sich
  beim Klick scheinbar nichts tun.

Selbst angelegte Einträge kannst du jederzeit über **„Eigenen Eintrag
entfernen“** wieder löschen.

### Reiter „Startmenü-Einträge“

Listet **alle** Startmenü-Einträge des Systems und zeigt, zu welchem Programm
sie gehören. Steht in der Spalte „Startbefehl“ **„Programm fehlt“**, zeigt der
Eintrag auf ein Programm, das es nicht mehr gibt. Der Eintrag ist dann
vermutlich ein Überbleibsel einer Deinstallation.

### Reiter „Paketverwaltungen“

![Übersicht der Paketverwaltungen](docs/screenshot-paketverwaltungen.png)

Zeigt, welche Paketverwaltungen, App-Stores und Update-Werkzeuge vorhanden sind
und wie viele Programme jeweils darüber installiert wurden. So siehst du zum
Beispiel, ob du irgendwann für eine Anleitung Snap oder Homebrew nachinstalliert
hast.

### Reiter „Hilfe“

Eine Kurzfassung dieser Anleitung direkt im Programm.

---

## Begriffe einfach erklärt

| Begriff | Erklärung |
|---|---|
| **Paket** | Ein Programm (oder Teil davon) in einer Form, die eine Paketverwaltung installieren, aktualisieren und entfernen kann. |
| **pacman** | Die Paketverwaltung von CachyOS bzw. Arch Linux. Sie kümmert sich um die offiziellen Pakete. |
| **Repo** (Repository) | Ein Online-Lager mit fertigen Paketen. CachyOS hat eigene Repos (`cachyos`, `cachyos-v3` …, für deinen Prozessor optimiert) und nutzt zusätzlich die von Arch Linux (`core`, `extra`, `multilib`). |
| **AUR** | Das *Arch User Repository*: eine riesige Sammlung von Bauanleitungen aus der Community. Nicht offiziell geprüft. Wird mit einem **AUR-Helfer** wie `paru` (bei CachyOS dabei) oder `yay` benutzt. |
| **Chaotic-AUR** | Ein zusätzliches, inoffizielles Repo mit fertig gebauten AUR-Paketen. Wird oft nach Anleitungen eingerichtet. |
| **Flatpak / Flathub** | Ein System für abgeschottete Apps, unabhängig von der Linux-Distribution. Flathub ist der größte Flatpak-„Store“. |
| **Snap** | Ähnlich wie Flatpak, stammt von Ubuntu. Unter CachyOS unüblich. |
| **AppImage** | Ein Programm in einer einzigen Datei, die man herunterlädt und direkt startet, ohne Installation. |
| **pipx / uv** | Werkzeuge, um Python-Programme sauber getrennt vom System zu installieren. |
| **cargo** | Werkzeug der Programmiersprache Rust. Kann Programme aus dem Quellcode bauen und installieren. |
| **npm** | Paketverwaltung für JavaScript/Node.js. |
| **Homebrew** | Paketverwaltung aus der macOS-Welt, gibt es auch für Linux. |
| **Abhängigkeit** | Ein Paket, das nicht du, sondern ein anderes Programm braucht, z. B. eine Bibliothek. Wird automatisch mitinstalliert. |
| **.desktop-Datei** | Eine kleine Textdatei, die einen Startmenü-Eintrag beschreibt (Name, Symbol, Startbefehl). Systemweite liegen in `/usr/share/applications`, deine eigenen in `~/.local/share/applications`. |
| **Systemupdate** | Unter CachyOS: `sudo pacman -Syu` aktualisiert alle Repo-Pakete, `paru` zusätzlich alle AUR-Pakete. Flatpaks werden mit `flatpak update` aktualisiert. |

---

## Welche Quellen werden erkannt?

| Quelle | Wie erkannt | Auto-Update beim Systemupdate? | Wie wird „Aktuell?“ geprüft |
|---|---|---|---|
| **Offizielles Repo** (CachyOS, Arch, Zusatz-Repos wie Chaotic-AUR) | `pacman -Qi`, `pacman -Sl` | ✔ ja (`pacman -Syu`, `paru`) | `checkupdates` (lädt eine frische Paketliste in einen temporären Ordner, ohne das System zu ändern) |
| **AUR** | `pacman -Qm` (Pakete, die in keinem Repo stehen) | ◐ nur mit AUR-Helfer (`paru`, `yay`), nicht mit reinem `pacman -Syu` | Abfrage der AUR-Webschnittstelle |
| **Flatpak** | `flatpak list --app` | ◐ mit `flatpak update` oder Discover/GNOME Software | `flatpak remote-ls --updates` |
| **Snap** | `snap list` | ✔ ja, snapd aktualisiert selbstständig | `snap refresh --list` |
| **AppImage** | Suche nach `*.AppImage` in `~/Applications`, `~/AppImages`, `~/Downloads`, `~/.local/bin`, `/opt` u. a. | ✘ nein | nicht möglich (keine zentrale Versionsliste) |
| **pipx** | `pipx list --json` | ✘ nein (`pipx upgrade-all`) | Abfrage bei PyPI |
| **uv tool** | `uv tool list` | ✘ nein (`uv tool upgrade --all`) | Abfrage bei PyPI |
| **cargo** | `cargo install --list` | ✘ nein | Abfrage bei crates.io |
| **npm** | `npm ls -g` (ohne die von pacman verwalteten) | ✘ nein (`npm update -g`) | `npm outdated -g` |
| **Homebrew** | `brew list --versions` | ✘ nein (`brew upgrade`) | `brew outdated` |
| **Manuell** | Programme in `~/.local/bin`, `~/bin`, `~/go/bin`, `/usr/local/bin` und Ordner in `/opt`, die keiner Paketverwaltung gehören | ✘ nein | nicht möglich |

Die Startmenü-Einträge werden aus allen üblichen Ordnern gelesen (inklusive
Flatpak- und Snap-Einträgen) und den Programmen so zugeordnet:

1. **Sicher:** Die Datei gehört laut pacman zum Paket, oder der Eintrag trägt die
   Flatpak-ID bzw. den Snap-Namen.
2. **Über den Startbefehl:** Der Eintrag startet eine Programmdatei, die zu
   einem Programm gehört (z. B. `~/.cargo/bin/rg` → ripgrep).

---

## Was ändert das Programm an meinem System?

| Aktion | Ändert etwas? |
|---|---|
| Programme einlesen | Nein, nur lesend |
| Nach Updates suchen | Nein. Es werden nur Versionsnummern aus dem Internet abgefragt. `checkupdates` arbeitet in einem temporären Ordner und fasst die Paketdatenbank des Systems nicht an. |
| Startmenü-Eintrag anlegen | Legt **eine** Datei `~/.local/share/applications/cachy-kompass-<name>.desktop` an |
| Eigenen Eintrag entfernen | Löscht nur Einträge, die der Software-Kompass selbst angelegt hat (erkennbar an `X-Cachy-Kompass=true` in der Datei) |
| Programme deinstallieren | **Macht der Software-Kompass nicht.** Er zeigt dir nur den passenden Befehl, den du selbst ins Terminal kopieren kannst. |

Für die Update-Prüfung werden folgende Adressen abgefragt (nur wenn du auf
„Nach Updates suchen“ klickst): die CachyOS/Arch-Paketspiegel (über
`checkupdates`), `aur.archlinux.org`, Flathub, der Snap Store, `pypi.org`,
`crates.io`, die npm-Registry und Homebrew.

---

## Textmodus für das Terminal

Alles gibt es auch ohne Oberfläche:

```bash
cachy-kompass --cli                 # Tabelle aller Programme
cachy-kompass --cli --updates       # … mit Update-Prüfung
cachy-kompass --cli --all           # … inklusive Abhängigkeiten/Bibliotheken
cachy-kompass --cli --installers    # … plus Liste der Paketverwaltungen
cachy-kompass --json > liste.json   # maschinenlesbar, z. B. als Sicherung deiner Programmliste
cachy-kompass --help                # alle Optionen
```

---

## Deinstallation

Im heruntergeladenen Ordner:

```bash
./uninstall.sh
```

Das Skript fragt nach, ob auch die selbst angelegten Startmenü-Einträge gelöscht
werden sollen. Die Pakete `pyside6` und `pacman-contrib` bleiben installiert;
falls du sie nicht mehr brauchst: `sudo pacman -Rns pyside6 pacman-contrib`.

---

## Häufige Fragen & Probleme

**Warum hat ein Programm keinen Startmenü-Eintrag?**
Viele Programme haben bewusst keinen: Kommandozeilenprogramme (z. B. `git`,
`htop`), Hintergrunddienste, Treiber. Nur wenn ein Programm mit Fenster fehlt,
lohnt sich ein eigener Eintrag.

**Warum steht bei einem AUR-Paket „unbekannt“?**
Entweder steht es nicht (mehr) im AUR (vielleicht selbst gebaut oder
verwaist), oder es ist eine Entwicklerversion (`-git`), bei der die
Versionsnummer im AUR nichts aussagt.

**Die Update-Prüfung für Repo-Pakete ist ungenau.**
Installiere `pacman-contrib` (`sudo pacman -S pacman-contrib`). Ohne das
Programm `checkupdates` vergleicht der Software-Kompass nur mit der zuletzt
heruntergeladenen Paketliste.

**Ein neu angelegter Eintrag erscheint nicht im Startmenü.**
Meist reicht es, das Startmenü kurz zu schließen und neu zu öffnen. Unter KDE
hilft notfalls `kbuildsycoca6` im Terminal oder ein Ab- und Anmelden.

**„Die grafische Oberfläche braucht PySide6“**
`sudo pacman -S pyside6` ausführen.

**Wie bringe ich alles auf einmal auf den neuesten Stand?**
Unter CachyOS am einfachsten im Terminal:
```bash
paru              # Repo- und AUR-Pakete
flatpak update    # Flatpaks
```
Für pipx, cargo, npm usw. steht der passende Befehl jeweils in der Detailansicht.
Wer es bequem mag, kann `topgrade` installieren, das aktualisiert alles mit
einem Befehl.

**Ich habe einen Fehler gefunden.**
Starte das Programm im Terminal mit `cachy-kompass -v`, damit ausführliche
Meldungen erscheinen, und eröffne ein Issue auf GitHub.

---

## Bekannte Grenzen

- Ausgelegt auf **CachyOS** (funktioniert ebenso unter Arch Linux und
  Arch-basierten Systemen wie EndeavourOS).
- **Nix**- und **Distrobox**-Programme werden nur als „vorhanden“ erkannt, aber
  nicht einzeln aufgelistet.
- Bei **AppImages** und **manuell** installierten Programmen gibt es keine
  zentrale Versionsliste, deshalb kann deren Aktualität nicht geprüft werden.
  Bei AppImages wird die Version aus dem Dateinamen geraten.
- Die Zuordnung von Startmenü-Einträgen über den Startbefehl ist eine gute
  Schätzung, aber nicht in jedem Sonderfall perfekt.
- Dass ein Programm „aktuell“ ist, bezieht sich auf den Zeitpunkt der Prüfung.

### Ideen für später

- Versteckte Einträge mit einem Klick wieder einblenden
- Kaputte Startmenü-Einträge direkt aufräumen
- Updates direkt aus dem Programm starten (mit Passwortabfrage)
- Nix-Profile und Distrobox-Container einzeln auflisten
- PKGBUILD, damit sich der Software-Kompass selbst über das AUR installieren lässt
- Englische Übersetzung

---

## Für Entwickler

Aufbau, Funktionsweise und wie man eine neue Installationsquelle hinzufügt,
stehen in [docs/ENTWICKLUNG.md](docs/ENTWICKLUNG.md).

Kurzfassung:

```bash
pip install pytest ruff     # oder: sudo pacman -S python-pytest ruff
pytest                      # Tests (laufen auch ohne CachyOS)
ruff check .                # Code-Stil
python -m cachy_kompass     # starten
```

## Lizenz

Noch keine Lizenz festgelegt. Ohne Lizenz dürfen andere den Code zwar ansehen,
aber nicht weiterverwenden. Wenn das Projekt offen sein soll, empfiehlt sich
z. B. die [MIT-](https://choosealicense.com/licenses/mit/) oder
[GPL-3.0-Lizenz](https://choosealicense.com/licenses/gpl-3.0/).
