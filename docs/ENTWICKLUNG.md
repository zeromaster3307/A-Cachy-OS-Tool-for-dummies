# Entwicklerdokumentation

Diese Seite erklärt, wie der Cachy Software-Kompass intern funktioniert und wie
man ihn erweitert. Für die Bedienung siehe die [README](../README.md).

## Technik in Kürze

| Was | Womit | Warum |
|---|---|---|
| Sprache | Python ≥ 3.10 | Unter CachyOS vorinstalliert, leicht lesbar |
| Oberfläche | Qt 6 über **PySide6** | Passt optisch zu KDE Plasma (Standard-Desktop von CachyOS), offizielles Paket `pyside6` in den Repos |
| Abhängigkeiten | nur die Python-Standardbibliothek (+ PySide6 für die GUI) | Kein `pip install` nötig, nichts kann kaputtgehen |
| Tests | pytest | Laufen ohne CachyOS, weil die Auswertung von den Systembefehlen getrennt ist |

## Ordnerstruktur

```
cachy_kompass/
├── __init__.py          Versionsnummer, App-Name
├── __main__.py          ermöglicht „python -m cachy_kompass“
├── app.py               Befehlszeile auswerten → GUI oder Textmodus starten
├── i18n.py              Übersetzung: _(), ngettext(), Sprache wählen, Datum/Zahlen
├── locale/en.po         englische Übersetzung aller Texte
├── cli.py               Textmodus (Tabelle / JSON)
├── models.py            Datenklassen (Program, DesktopEntry …) und ALLE
│                        erklärenden Texte zu den Quellen (SOURCE_INFO)
├── util.py              Befehle ausführen, HTTP-Abfragen, Versionsvergleich
├── scanner.py           Ablaufsteuerung: Quellen → Startmenü → Datum/Größe/Doppelte →
│                        Paketverwaltungen;
│                        Update-Prüfung
├── desktop.py           .desktop-Dateien lesen, zuordnen, anlegen, löschen
├── installers.py        Erkennung, Einstufung und Installationsplan für
│                        Paketverwaltungen / App-Stores
├── terminal.py          Befehle sichtbar in einem Terminalfenster ausführen
├── cleanup.py           Prüfungen für den Reiter „Aufräumen“ (nur lesend)
├── history.py           pacman-Protokoll: Installationsdatum, Neustart-Hinweis
├── sizes.py             belegter Speicherplatz je Programm
├── duplicates.py        doppelt installierte Programme erkennen
├── update_all.py        Update-Schritte für „Alles aktualisieren“
├── backup.py            Programmliste als Wiederherstellungs-Skript
├── sources/             eine Datei pro Installationsquelle
│   ├── base.py          Basisklasse PackageSource
│   ├── pacman.py        Repos + AUR
│   ├── flatpak.py
│   ├── snap.py
│   ├── python_tools.py  pipx, uv tool
│   ├── devtools.py      cargo, npm, Homebrew
│   └── files.py         AppImages, manuell installierte Programme
└── gui/
    ├── main_window.py   Hauptfenster mit Reitern
    ├── table_model.py   Tabellenmodell + Filter
    ├── details.py       HTML für Detailansicht und Hilfe
    ├── entry_dialog.py  Dialog „Startmenü-Eintrag anlegen / bearbeiten“
    ├── update_dialog.py Dialog „Alles aktualisieren“
    ├── cleanup_tab.py   Reiter „Aufräumen“
    └── workers.py       Hintergrund-Threads (damit die GUI nicht einfriert)
tests/                   pytest-Tests mit Beispielausgaben der echten Befehle
tools/i18n.py            Texte sammeln und en.po abgleichen bzw. prüfen
install.sh / uninstall.sh
```

## Ablauf

```
            ┌────────────────────────┐
 Start ───▶ │ scanner.scan()         │  (läuft im Hintergrund-Thread)
            └──────────┬─────────────┘
                       │ für jede Quelle in sources.all_sources():
                       │   is_available()? → scan(ctx) → list[Program]
                       ▼
            ┌────────────────────────┐
            │ desktop.load_entries() │  alle .desktop-Dateien, Benutzerordner gewinnt
            │ desktop.match_entries()│  Einträge den Programmen zuordnen
            └──────────┬─────────────┘
                       ▼
            ┌────────────────────────┐
            │ installers.detect()    │  welche Paketverwaltungen gibt es?
            └──────────┬─────────────┘
                       ▼
                  ScanResult  ──▶ GUI-Tabelle / Textausgabe

 „Nach Updates suchen“:
   scanner.check_updates(programs)
     → gruppiert nach Quelle (PackageSource.handles)
     → ruft check_updates() jeder Quelle parallel auf
     → liefert {Program.key: UpdateResult}
   scanner.apply_updates() überträgt das Ergebnis im Hauptthread
```

Wichtige Grundsätze:

- **Auswerten getrennt vom Ausführen.** Jede Quelle hat reine Funktionen wie
  `parse_qi(text)`, die nur Text bekommen. Das macht sie testbar ohne pacman.
- **`LC_ALL=C`** beim Ausführen von Befehlen (siehe `util.run`), damit die
  Ausgabe immer englisch und damit auswertbar ist.
- **Eine kaputte Quelle bricht nicht alles ab.** Fehler landen in
  `ScanResult.warnings`.
- **Hintergrund-Threads verändern keine Objekte, die die GUI anzeigt.** Die
  Update-Prüfung liefert ein Wörterbuch, übernommen wird im Hauptthread.
- **Nichts kaputt machen.** Gelöscht werden nur Startmenü-Einträge im
  Benutzerordner (nach Rückfrage), Programme werden nie deinstalliert.
- **Nie selbst root.** Was Administratorrechte braucht (Installieren von
  Paketverwaltungen), läuft sichtbar über `terminal.run_in_terminal()` – der
  Nutzer sieht den Befehl und gibt das Passwort selbst ein. Installiert wird
  nur, was `installers.plan_install()` erlaubt: nie „nicht empfohlene“
  Werkzeuge, nur aus offiziellen Repos (geprüft per `pacman -Si`).

## Eine neue Installationsquelle hinzufügen

Beispiel: Nix-Profile sollen einzeln aufgelistet werden.

1. In `models.py` einen neuen Wert in `Source` anlegen (`NIX = "nix"`) und in
   `SOURCE_INFO` die Texte dazu schreiben: Beschriftung, wie installiert,
   ob Auto-Update, Update-Hinweis, Deinstallationsbefehl.
2. In `sources/` eine Klasse schreiben:

   ```python
   class NixSource(PackageSource):
       title = "Nix"
       handles = (Source.NIX,)

       def is_available(self) -> bool:
           return util.which("nix") is not None

       def scan(self, ctx: ScanContext) -> list[Program]:
           out = util.run(["nix", "profile", "list", "--json"]) or ""
           return [Program(name=..., version=..., source=Source.NIX) for ... in parse(out)]

       def check_updates(self, programs):   # optional
           ...
   ```

   Die Auswertung (`parse(out)`) als eigene Funktion schreiben und in
   `tests/test_parsers.py` mit einer echten Beispielausgabe testen.
3. Die Klasse in `sources/__init__.py` in `all_sources()` eintragen, **vor**
   `ManualSource`.
4. Falls die Programmdateien in einem eigenen Ordner liegen: diesen Ordner in
   `sources/files.py` → `MANAGED_PREFIXES` eintragen, damit sie nicht
   zusätzlich als „manuell“ auftauchen.
5. Optional in `installers.py` einen `InstallerSpec` ergänzen.

Die Oberfläche passt sich automatisch an (Filter-Auswahl, Hilfe-Text,
Spalten).

## Tests & Code-Stil

```bash
pytest -q          # alle Tests
ruff check .       # Code-Stil / typische Fehler
ruff check --fix . # automatisch behebbare Dinge korrigieren
```

Die Tests laufen bei jedem Push automatisch über GitHub Actions
(`.github/workflows/tests.yml`).

Die Oberfläche lässt sich auch ohne Bildschirm starten (z. B. für Screenshots
oder automatische Tests):

```bash
QT_QPA_PLATFORM=offscreen python -m cachy_kompass
```

## Konventionen

- Alles, was Nutzer lesen, ist **deutsch** im Code, für Laien formuliert und mit
  `_()` markiert (siehe unten). Programmcode-Namen sind englisch, Kommentare deutsch.
- Erklärende Texte zu Quellen gehören nach `models.SOURCE_INFO`, nicht verstreut
  in die GUI.
- Neue Funktionen, die etwas am System ändern, müssen vorher nachfragen und
  dürfen nur Dinge im Benutzerordner anfassen.

## Texte und Übersetzungen

Deutsch ist die Grundsprache: Alle Texte stehen deutsch im Code, die englische
Übersetzung liegt in `cachy_kompass/locale/en.po`. Die Sprache wird einmal beim
Start festgelegt (`--lang`, sonst `CACHY_KOMPASS_LANG`, sonst die
Systemsprache) – vor dem Laden der übrigen Module. Deshalb dürfen auch Texte,
die schon beim Import entstehen (z. B. `SOURCE_INFO`, `installers.SPECS`),
`_()` benutzen.

Regeln für neue Texte:

```python
from cachy_kompass.i18n import _, ngettext

_("Fertig.")                                             # einfacher Text
_("Eintrag angelegt: {path}").format(path=p)             # mit Platzhalter – nie f-Strings in _()
ngettext("{n} Paket", "{n} Pakete", n).format(n=n)       # Ein-/Mehrzahl
i18n.date(dt), i18n.date_time(dt), util.format_size(b)   # Datum und Größen passend zur Sprache
```

- In `_()` muss ein **fester Text** stehen (keine Variable, kein f-String),
  sonst findet ihn `tools/i18n.py` nicht.
- Benannte Platzhalter (`{name}`) statt Text-Stückelung: Im Englischen ändert
  sich oft die Satzstellung.
- In Funktionen, die `_()` aufrufen, `_` nicht als Wegwerf-Variable benutzen
  (`path, _filter = …` statt `path, _ = …`).
- HTML-Tags dürfen im Text stehen; die Übersetzung muss dieselben Tags haben.

Nach dem Ändern von Texten:

```bash
python tools/i18n.py update   # neue Texte in en.po eintragen, entfernte löschen
# … in en.po die leeren msgstr "" übersetzen …
python tools/i18n.py check    # meldet fehlende Übersetzungen und falsche Platzhalter
```

Der Test `tests/test_i18n.py` führt dieselbe Prüfung aus, eine unvollständige
Übersetzung fällt also auch in GitHub Actions auf. Eine weitere Sprache kommt
dazu, indem man `en.po` nach `<sprache>.po` kopiert und die `msgstr` übersetzt.

