# 🧭 Cachy Software-Kompass

🇬🇧 [English version](README.en.md)

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

> **Sicher:** Der Software-Kompass bekommt nie selbst Administratorrechte.
> Einlesen und Prüfen ändern nichts. Selbst ändert er nur Startmenü-Einträge in
> deinem eigenen Benutzerordner. Alles andere – Aufräumen, „Alles aktualisieren“,
> eine Paketverwaltung nachinstallieren – startet er nur auf deinen Klick und nach
> Rückfrage, sichtbar in einem Terminalfenster, in dem du selbst dein Passwort
> eingibst und pacman bzw. flatpak noch einmal nachfragen. Programme deinstalliert
> er nie, er zeigt dir nur den passenden Befehl. Genaueres steht unter
> [Was ändert das Programm an meinem System?](#was-ändert-das-programm-an-meinem-system)

---

## Inhalt

1. [Installation](#installation)
2. [Starten](#starten)
3. [Sprache](#sprache)
4. [Bedienung](#bedienung)
5. [Begriffe einfach erklärt](#begriffe-einfach-erklärt)
6. [Welche Quellen werden erkannt?](#welche-quellen-werden-erkannt)
7. [Was ändert das Programm an meinem System?](#was-ändert-das-programm-an-meinem-system)
8. [Textmodus für das Terminal](#textmodus-für-das-terminal)
9. [Deinstallation](#deinstallation)
10. [Häufige Fragen & Probleme](#häufige-fragen--probleme)
11. [Bekannte Grenzen](#bekannte-grenzen)
12. [Für Entwickler](#für-entwickler)

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

### Auf eine neue Version aktualisieren

Im heruntergeladenen Ordner:

```bash
cd A-Cachy-OS-Tool-for-dummies
git pull          # neuesten Stand herunterladen
./install.sh      # installierte Version ersetzen
```

Wichtig: `git clone` bzw. `git pull` laden nur den Code herunter. Erst
`./install.sh` ersetzt das Programm, das im Startmenü startet. Danach den
Software-Kompass einmal schließen und neu öffnen.

Die alte Version musst du **nicht** vorher löschen, sie wird automatisch
ersetzt. Selbst angelegte Startmenü-Einträge bleiben erhalten.

**Welche Version habe ich?** Die Versionsnummer steht im Fenstertitel und oben
im Reiter „Hilfe“, im Terminal zeigt sie `cachy-kompass --version`. Was sich
zwischen den Versionen geändert hat, steht in [CHANGELOG.md](CHANGELOG.md).

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

## Sprache

Die Oberfläche gibt es auf **Deutsch** und **Englisch**. Der Software-Kompass
richtet sich nach der Systemsprache: Auf einem englischen System startet er
englisch, sonst deutsch.

Selbst wählen geht so:

```bash
cachy-kompass --lang en      # Englisch
cachy-kompass --lang de      # Deutsch
```

Soll er auch aus dem Startmenü immer in einer bestimmten Sprache starten, lege
die Datei `~/.config/environment.d/cachy-kompass.conf` mit dieser Zeile an und
melde dich einmal ab und wieder an:

```
CACHY_KOMPASS_LANG=en
```

---

## Bedienung

### Reiter „Programme“

Die Hauptansicht. Jede Zeile ist ein Programm.

| Spalte | Bedeutung |
|---|---|
| **Programm** | Name des Programms (wenn möglich so, wie er im Startmenü steht). **(2×)** dahinter heißt: doppelt installiert, z. B. aus dem Repo und zusätzlich als Flatpak |
| **Version** | installierte Version |
| **Quelle** | auf welchem Weg es installiert wurde (siehe [Begriffe](#begriffe-einfach-erklärt)) |
| **Art** | 🪟 **App** (Programm mit Fenster) · ⌨ **Befehl** (Kommandozeilenprogramm fürs Terminal) · 📦 **Sonstiges** (nicht startbar: Schriftarten, Treiber, Firmware, Bibliotheken, Designs, Sammelpakete) |
| **Startmenü** | ✔ sichtbar · ◐ Eintrag vorhanden, aber ausgeblendet · ✘ kein Eintrag |
| **Auto-Update** | ✔ wird beim Systemupdate mit aktualisiert · ◐ nur mit dem richtigen Werkzeug · ✘ musst du selbst aktualisieren |
| **Aktuell?** | erst nach Klick auf **„Nach Updates suchen“**: ✔ aktuell · ⬆ neuere Version verfügbar |
| **Größe** | belegter Speicherplatz. Bei Flatpaks nur die App selbst, gemeinsam genutzte Laufzeiten kommen hinzu |
| **Installiert** | wann das Programm installiert wurde. Bei Repo- und AUR-Paketen genau (aus dem Protokoll von pacman). **„ca.“** heißt: Datum der Programmdateien, denn bei Flatpak, AppImage usw. gibt es kein Protokoll (nach einem Update steht dort evtl. das Update-Datum) |
| **Beschreibung** | Kurzbeschreibung des Pakets |

Ein Klick auf ein Programm zeigt rechts alle Details: woher es kommt, wie es
aktualisiert wird, welche Startmenü-Einträge es hat und mit welchem Befehl man
es wieder deinstalliert. Außerdem:

- **Warum ist das installiert?** Bei Repo- und AUR-Paketen steht dort, welche
  Programme es brauchen. So erfährst du bei einer Abhängigkeit, wer sie
  mitgebracht hat.
- **Was ginge beim Deinstallieren mit weg?** Ein Trockenlauf von pacman zeigt,
  welche nicht mehr benötigten Abhängigkeiten mit entfernt würden und wie viel
  Platz das bringt. Wird das Paket noch von einem anderen gebraucht, steht dort
  stattdessen, von welchem.
- **Doppelt installiert:** ein Hinweis, falls es dasselbe Programm noch aus einer
  anderen Quelle gibt.
- **Starten über das Terminal:** der Befehl, mit dem du das Programm im Terminal
  oder über **Alt+F2** (KRunner) startest, z. B. `vlc`. Das klappt auch, wenn der
  Startmenü-Eintrag ausgeblendet ist. Mit **„Startbefehl kopieren“** landet er in
  der Zwischenablage.

Ein Klick auf eine Spaltenüberschrift sortiert die Liste, zum Beispiel nach
„Aktuell?“, dann stehen alle veralteten Programme oben.

**Werkzeugleiste oben** (erste Zeile: Aktionen und Suche, zweite Zeile: Filter):

| Element | Funktion |
|---|---|
| **Neu einlesen** (F5) | sucht alle Programme erneut |
| **Nach Updates suchen** | fragt im Internet nach neueren Versionen; dabei wird **nichts** installiert |
| **Alles aktualisieren …** | installiert alle Updates, siehe [unten](#alles-aktualisieren) |
| **Liste sichern …** | speichert alle installierten Programme als Skript, siehe [unten](#programmliste-sichern) |
| **Suchen …** | filtert **alle Reiter** gleichzeitig: Namen, Beschreibungen, Namen der Startmenü-Einträge (z. B. „Claude Code“ für das Programm `claude`), Befehle und Pfade |
| **Alle Quellen** | zeigt nur Programme aus einer bestimmten Quelle, z. B. nur Flatpaks |
| **Art: …** | Ausklappliste mit Häkchen (☑ Apps ☐ Befehle ☐ Sonstiges), frei kombinierbar. Auf der Schaltfläche steht, was gerade ausgewählt ist. Standard ist **nur Apps**, also Programme mit Fenster. Häkchen bei „Befehle“ zeigt zusätzlich Kommandozeilenprogramme, bei „Sonstiges“ auch Schriftarten, Treiber usw. Der Filter gilt auch im Reiter „Startmenü-Einträge“. |
| **Startmenü: …** | zeigt z. B. nur Programme **ohne** Startmenü-Eintrag |
| **Installiert: …** | nur Programme, die in den letzten 7 Tagen, 30 Tagen oder im letzten Jahr installiert wurden. Praktisch für die Frage „Was habe ich letzte Woche nach dieser Anleitung installiert?“ |
| **Weitere Filter** | Ausklappliste mit Häkchen. In Klammern steht, wie viele davon aktiv sind: |
| &nbsp;&nbsp;↳ **Nur veraltete** | zeigt nur Programme mit verfügbarem Update |
| &nbsp;&nbsp;↳ **Nur ohne Auto-Update** | zeigt nur Programme, um deren Updates du dich selbst kümmern musst |
| &nbsp;&nbsp;↳ **Nur doppelt installierte** | zeigt nur Programme, die es aus mehreren Quellen gibt |
| &nbsp;&nbsp;↳ **Abhängigkeiten zeigen** | blendet auch Bibliotheken und automatisch mitinstallierte Pakete ein (das sind oft über 1000) |

### Alles aktualisieren

**„Alles aktualisieren …“** zeigt, welche Updates auf deinem System anstehen
können, mit je einem Häkchen:

- **System + AUR** mit `paru -Syu` (ohne paru: `yay -Syu` bzw. `sudo pacman -Syu`)
- **Flatpak-Apps** mit `flatpak update`
- falls vorhanden: **pipx**, **uv**, **cargo** (nur mit `cargo-update`) und **Homebrew**

Nach **„Terminal öffnen“** laufen die Befehle nacheinander sichtbar in einem
Terminalfenster. Dort gibst du dein Passwort ein und bestätigst die
Installation. Geht ein Schritt schief oder brichst du ab, werden die folgenden
nicht mehr ausgeführt. Was nicht automatisch aktualisiert werden kann (z. B.
AppImages), steht im Dialog unter „Nicht dabei“.

**Neustart-Hinweis:** Wurden seit dem letzten Start der Kernel, der
Grafiktreiber (NVIDIA, Mesa), systemd, glibc oder die Firmware aktualisiert,
erscheint oben im Fenster ein orangefarbener Hinweis **„Neustart empfohlen“**.
Diese Updates wirken erst nach einem Neustart. Nach dem Update also auf
**„Neu einlesen“** klicken.

### Programmliste sichern

**„Liste sichern …“** speichert alle bewusst installierten Programme in eine
Datei, z. B. `programme-2026-10-03.sh`. Die Datei ist beides:

- eine **lesbare Liste**, was du alles installiert hast (einfach mit einem
  Texteditor öffnen), und
- ein **Skript**, das nach einer Neuinstallation von CachyOS alles wieder
  einspielt: Repo-Pakete, AUR-Pakete, Flatpaks, Snaps, pipx, uv, cargo, npm und
  Homebrew.

So stellst du die Programme wieder her:

1. Die Datei vor der Neuinstallation auf einen USB-Stick oder in die Cloud kopieren.
2. Auf dem neuen System im Terminal `bash programme-2026-10-03.sh` ausführen.
   Wichtig: ausdrücklich `bash` davor schreiben, denn CachyOS nutzt die fish-Shell.
3. Vor jedem Abschnitt (z. B. „23 Pakete aus den offiziellen Repos installieren?“)
   wird nachgefragt. Mit `n` überspringst du ihn.

AppImages und von Hand installierte Programme kann das Skript nicht
herunterladen. Sie stehen als Merkliste am Ende. **Einstellungen und eigene
Dateien sind nicht enthalten**, die liegen in deinem Benutzerordner (z. B.
`~/.config`) und gehören in eine normale Datensicherung.

### Einen Startmenü-Eintrag anlegen

1. Programm in der Liste auswählen
2. **„Startmenü-Eintrag anlegen …“** klicken (oder Doppelklick auf die Zeile)
3. Die Felder sind schon sinnvoll vorausgefüllt. Prüfen und auf **„Eintrag anlegen“** klicken.

![Dialog zum Anlegen eines Eintrags](docs/screenshot-eintrag-anlegen.png)

- **Startbefehl:** Was beim Klick auf den Eintrag ausgeführt wird. Normalerweise
  passt der Vorschlag.
- **Symbol:** Der Name eines Symbols aus deinem Symbol-Design oder eine eigene
  Bilddatei über **„Bild wählen …“**. Unter dem Feld steht, ob ein passendes
  Symbol gefunden wurde. Falls nicht, lade z. B. das Logo von der Webseite des
  Programms herunter und wähle es aus.
  - Am besten eignen sich **SVG** oder **PNG**. JPG, ICO, WebP usw. werden
    automatisch in PNG umgewandelt.
  - Das Bild wird nach `~/.local/share/icons/cachy-kompass/` **kopiert**. Du
    kannst die heruntergeladene Datei danach also ruhig löschen.
- **In einem Terminalfenster starten:** Für Programme ohne eigenes Fenster
  (Kommandozeilenprogramme wie `yt-dlp` oder `htop`). Ohne Häkchen würde sich
  beim Klick scheinbar nichts tun.

### Einen Startmenü-Eintrag entfernen

Über **„Eintrag entfernen …“** (oder im Reiter „Startmenü-Einträge“) lassen
sich alle Einträge löschen, die in **deinem Benutzerordner** liegen
(`~/.local/share/applications`):

- Einträge, die der Software-Kompass angelegt hat, werden mitsamt ihrem
  kopierten Symbol entfernt.
- Einträge, die du selbst oder ein anderes Programm angelegt hat (z. B. von
  Hand, mit Claude, über Steam, Gear Lever oder AppImageLauncher), lassen sich
  ebenfalls entfernen. Vorher erscheint aber ein deutlicher Warnhinweis.
- Ersetzt ein Benutzereintrag einen Systemeintrag gleichen Namens, weist der
  Software-Kompass darauf hin. Nach dem Löschen erscheint dann wieder der
  ursprüngliche Systemeintrag.
- **Systemeinträge** (`/usr/share/applications` usw.) gehören zu Paketen und
  werden **nie** gelöscht. Sie verschwinden, wenn man das Programm deinstalliert.

Das Programm selbst bleibt dabei immer installiert, nur der Menüeintrag
verschwindet.

### Einträge bearbeiten, ein- und ausblenden

Im Reiter **„Startmenü-Einträge“** gibt es drei Knöpfe für den ausgewählten Eintrag:

- **Bearbeiten …** ändert Name, Beschreibung, Startbefehl, Symbol, Kategorie und
  „Im Terminal starten“. Geändert wird nur, was du tatsächlich anpasst.
- **Einblenden / Ausblenden** zeigt einen versteckten Eintrag im Startmenü bzw.
  versteckt ihn. Beim Ausblenden erscheint der Befehl, mit dem du das Programm
  weiterhin im Terminal oder über Alt+F2 starten kannst. In der Spalte
  „Sichtbar“ steht dann „nein (von dir)“. Wählst du im Reiter „Programme“ bei einem Programm mit nur
  verstecktem Eintrag „Startmenü-Eintrag anlegen …“, wird das Einblenden
  ebenfalls angeboten.
- **Entfernen … / Original wiederherstellen …** (siehe oben).

**Systemeinträge bleiben dabei immer unverändert.** Stattdessen speichert der
Software-Kompass deine Fassung unter gleichem Namen in deinem Benutzerordner.
Sie ersetzt den Systemeintrag im Startmenü. Mit **„Original
wiederherstellen …“** löschst du deine Fassung, und der ursprüngliche Eintrag
gilt wieder. Hinweis: Ändert ein späteres Update den Systemeintrag, gilt
trotzdem weiter deine Fassung, bis du sie entfernst.

### Reiter „Startmenü-Einträge“

Listet **alle** Startmenü-Einträge des Systems und zeigt, zu welchem Programm
sie gehören. Die Spalte „Startbefehl“ zeigt, wie du das Programm auch im Terminal
oder über Alt+F2 startest (**„Startbefehl kopieren“** kopiert ihn). Steht dort
**„Programm fehlt“**, zeigt der
Eintrag auf ein Programm, das es nicht mehr gibt. Der Eintrag ist dann
vermutlich ein Überbleibsel einer Deinstallation.

Auch hier gibt es die Spalte **„Art“** (die Art des zugehörigen Programms), und es gilt derselbe Filter „Art“ wie in der Programmliste.

### Reiter „Paketverwaltungen“

![Übersicht der Paketverwaltungen](docs/screenshot-paketverwaltungen.png)

Zeigt, welche Paketverwaltungen, App-Stores und Update-Werkzeuge vorhanden sind
und wie viele Programme jeweils darüber installiert wurden. So siehst du zum
Beispiel, ob du irgendwann für eine Anleitung Snap oder Homebrew nachinstalliert
hast.

Jedes Werkzeug hat eine **Einstufung** mit Begründung:

| Einstufung | Bedeutung | Beispiele |
|---|---|---|
| ✔ **empfohlen** | passt gut zu CachyOS, risikoarm | Flatpak, paru, CachyOS Package Installer, cachy-update |
| ◐ **bei Bedarf** | nützlich, wenn man es braucht, sonst überflüssig | pipx, uv, Gear Lever, Topgrade, Discover, Distrobox |
| ✘ **nicht empfohlen** | doppelt, am System vorbei oder unter Arch unüblich | Snap, Homebrew, Nix, pip, yay (neben paru), Pamac |

**Installieren:** Fehlt ein Werkzeug, das „empfohlen“ oder „bei Bedarf“ ist,
kannst du es mit **„Installieren …“** nachinstallieren. Dabei gilt:

- Es wird **nur aus den offiziellen Paketquellen** installiert (CachyOS/Arch).
  Der Software-Kompass prüft vorher mit `pacman -Si`, ob das Paket dort wirklich
  verfügbar ist. Einzige Ausnahme: Gear Lever wird von Flathub geholt, wenn es
  nicht in den Repos ist und Flatpak schon vorhanden ist.
- **Nichts aus dem AUR, keine Skripte aus dem Internet.**
- Der Befehl läuft **sichtbar in einem Terminalfenster** (z. B. Konsole). Dort
  gibst du selbst dein Passwort ein, und pacman fragt vor der Installation noch
  einmal nach. Der Software-Kompass bekommt nie Administratorrechte.
- „Nicht empfohlene“ Werkzeuge bekommen **keinen** Installieren-Knopf, nur die
  Begründung und eine bessere Alternative.
- **Entfernen** geht bewusst nicht per Knopf. Entfernt man eine
  Paketverwaltung, verschwinden auch alle Programme, die darüber installiert
  wurden. Die Detailansicht zeigt dazu die Anzahl der betroffenen Programme und
  den Befehl.

### Reiter „Aufräumen“

![Reiter Aufräumen](docs/screenshot-aufraeumen.png)
<sub>(Screenshot mit Beispieldaten)</sub>

Ein Klick auf **„Jetzt prüfen“** sucht nach Dingen, die unnötig Platz belegen
oder kaputt sind. Das Prüfen selbst verändert nichts.

| Fund | Was ist das? | Aufräumen |
|---|---|---|
| **Verwaiste Pakete** | Abhängigkeiten, die kein Programm mehr braucht | `sudo pacman -Rns …`, pacman zeigt vorher die Liste |
| **Paket-Zwischenspeicher** | alte Paketversionen in `/var/cache/pacman/pkg`, oft mehrere GB | `paccache` behält die 2 neuesten Versionen jedes Pakets (für den Notfall-Rückweg) |
| **AUR-Bauordner** | Reste vom Bauen aus dem AUR (paru/yay) in `~/.cache` | Ordner löschen, werden beim nächsten Update neu angelegt |
| **Unbenutzte Flatpak-Laufzeiten** | Laufzeiten, die keine App mehr braucht | `flatpak uninstall --unused`, Flatpak zeigt vorher die Liste |
| **Kaputte Startmenü-Einträge** | Einträge, deren Programm fehlt | Einträge in deinem Benutzerordner werden direkt entfernt |
| **Doppelt installiert** | dasselbe Programm aus mehreren Quellen, z. B. Repo und Flatpak (erkannt am Namen) | **kein Knopf**, nur Erklärung und die Befehle zum Entfernen, denn du entscheidest, welche Fassung bleibt |
| **Nicht mehr im AUR** | AUR-Pakete, die dort nicht mehr stehen und keine Updates mehr bekommen | **kein Knopf**, nur Erklärung und Befehl, denn du entscheidest selbst |

Oben steht, wie viel Platz sich insgesamt gewinnen lässt. Mit **„Aufräumen …“**
öffnet sich nach einer Rückfrage ein Terminalfenster mit den angezeigten
Befehlen. Dort siehst du alles und bestätigst selbst. Danach erneut auf
„Jetzt prüfen“ klicken.

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
   einem Programm gehört (z. B. `~/.cargo/bin/rg` → ripgrep). Dabei wird hinter
   Terminals und Shells geschaut: Ein Eintrag mit `konsole -e claude` oder
   `sh -c "cd ~/Projekte && claude"` gehört zu `claude`, nicht zu Konsole.

---

## Was ändert das Programm an meinem System?

| Aktion | Ändert etwas? |
|---|---|
| Programme einlesen | Nein, nur lesend |
| Nach Updates suchen | Nein. Es werden nur Versionsnummern aus dem Internet abgefragt. `checkupdates` arbeitet in einem temporären Ordner und fasst die Paketdatenbank des Systems nicht an. |
| Startmenü-Eintrag anlegen | Legt **eine** Datei `~/.local/share/applications/cachy-kompass-<name>.desktop` an, bei eigenem Bild zusätzlich eine Kopie in `~/.local/share/icons/cachy-kompass/` |
| Eintrag entfernen | Löscht nur Einträge aus deinem Benutzerordner, nach Rückfrage. Bei fremden Einträgen gibt es eine zusätzliche Warnung. Systemeinträge werden nie angefasst. |
| Eintrag bearbeiten, ein-/ausblenden | Ändert Einträge in deinem Benutzerordner. Bei Systemeinträgen entsteht dort eine geänderte Kopie, das Original bleibt unverändert. |
| Alles aktualisieren | Nur nach Rückfrage, sichtbar in einem Terminalfenster, in dem du selbst dein Passwort eingibst und die Installation bestätigst |
| Liste sichern | Speichert eine Datei dort, wo du es auswählst. Ändert sonst nichts. |
| Details anzeigen | „Was ginge beim Deinstallieren mit weg?“ nutzt `pacman -Rsp`, einen reinen Trockenlauf ohne Administratorrechte |
| Aufräumen | Prüfen ändert nichts. Aufgeräumt wird nur nach Rückfrage, sichtbar in einem Terminalfenster; pacman, paccache und flatpak fragen dort zusätzlich nach. Nur kaputte Startmenü-Einträge im Benutzerordner löscht der Software-Kompass selbst. |
| Paketverwaltung installieren | Nur nach Rückfrage, nur aus den offiziellen Paketquellen, sichtbar in einem Terminalfenster, in dem du selbst dein Passwort eingibst |
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
cachy-kompass --lang en --cli       # auf Englisch, egal welche Systemsprache
cachy-kompass --help                # alle Optionen
```

---

## Deinstallation

Im heruntergeladenen Ordner:

```bash
./uninstall.sh
```

Das Skript fragt nach, ob auch die selbst angelegten Startmenü-Einträge (und deren Symbole) gelöscht
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
- **Doppelte** werden am Namen erkannt. Ganz selten sind zwei gleichnamige
  Programme aber verschiedene Dinge. Deshalb gibt es dafür keinen Aufräum-Knopf.
- Das **Installationsdatum** stammt bei Repo- und AUR-Paketen aus
  `/var/log/pacman.log`. Wurde das Protokoll gelöscht, fehlt das Datum.

### Ideen für später

- Nix-Profile und Distrobox-Container einzeln auflisten
- PKGBUILD, damit sich der Software-Kompass selbst über das AUR installieren lässt

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
python tools/i18n.py check  # sind alle Texte übersetzt?
```

Texte stehen auf Deutsch im Code und werden mit `_("…")` markiert, die englische
Übersetzung liegt in `cachy_kompass/locale/en.po` (siehe
[docs/ENTWICKLUNG.md](docs/ENTWICKLUNG.md#texte-und-übersetzungen)).

## Lizenz

Copyright © 2026 zeromaster3307 und Mitwirkende

Der Cachy Software-Kompass ist freie Software unter der
**GNU General Public License, Version 3 oder später** (GPL-3.0-or-later).
Den vollständigen Lizenztext findest du in der Datei [LICENSE](LICENSE).

Kurz gesagt (ohne rechtliche Verbindlichkeit):

- Du darfst das Programm **benutzen, weitergeben und verändern**, auch kommerziell.
- Wenn du eine **veränderte Version weitergibst**, muss sie ebenfalls unter der
  GPL stehen, und der Quellcode muss mitgeliefert bzw. zugänglich gemacht werden.
- Es gibt **keine Garantie**: Die Nutzung erfolgt auf eigene Verantwortung.
