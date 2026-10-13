# Änderungen

Hier steht, was sich von Version zu Version geändert hat. Die installierte
Version siehst du im Fenstertitel, im Reiter „Hilfe“ oder mit
`cachy-kompass --version`.

## 0.6.0

- **Englische Oberfläche:** Der Software-Kompass gibt es jetzt auch auf
  Englisch – Oberfläche, Hilfe, Textmodus, Terminal-Meldungen und das
  Wiederherstellungs-Skript von „Liste sichern“. Die Sprache richtet sich nach
  der Systemsprache; mit `--lang en` bzw. `--lang de` oder der Variable
  `CACHY_KOMPASS_LANG` lässt sie sich festlegen. Datum und Zahlen werden passend
  geschrieben (`2026-10-03`, `1.2 GB`).
- **README auf Englisch:** [README.en.md](README.en.md).
- Kleinigkeiten: „1 Paket“ statt „1 Pakete“ in Statuszeile, Aufräumen und
  Wiederherstellungs-Skript.
- Für Entwickler: Texte werden mit `_()` markiert, `python tools/i18n.py check`
  meldet fehlende Übersetzungen (siehe docs/ENTWICKLUNG.md).

## 0.5.3

- **Behoben:** Der Software-Kompass zeigte bei sich selbst nur die Größe des
  kleinen Startbefehls (etwa 190 Bytes). Jetzt zählt der ganze Programmordner
  mit. Die Details nennen außerdem den Weg zum Aktualisieren
  (`git pull` und `./install.sh`).
- **README und Hilfe:** Der Hinweis „verändert nichts am System“ war seit
  Aufräumen, „Alles aktualisieren“ und dem Nachinstallieren von
  Paketverwaltungen veraltet. Er beschreibt jetzt genau, was der
  Software-Kompass selbst tut und was nur auf Klick im Terminal läuft.

## 0.5.2

- **Startbefehl überall sichtbar:** Die Details zeigen, wie man ein Programm im
  Terminal oder über Alt+F2 startet (z. B. `vlc`), mit Knopf „Startbefehl
  kopieren“. Im Reiter „Startmenü-Einträge“ steht der Befehl in der Spalte
  „Startbefehl“, und beim Ausblenden eines Eintrags erscheint ein Hinweis, wie
  das Programm weiterhin startet.

## 0.5.1

- **Behoben:** Wurde der Startmenü-Eintrag eines Programms (z. B. VLC)
  ausgeblendet, galt das Programm danach als „Befehl“ und verschwand beim
  Standard-Filter „Apps“ aus beiden Reitern. Selbst ausgeblendete Programme
  bleiben jetzt „Apps“; im Reiter „Startmenü-Einträge“ steht bei „Sichtbar“
  „nein (von dir)“, und die Details erklären, wie man den Eintrag wieder einblendet.

## 0.5.0

- **Alles aktualisieren …:** startet System- und AUR-Update (paru), Flatpak-,
  pipx- und uv-Updates usw. sichtbar in einem Terminalfenster – jeder Schritt
  einzeln abwählbar.
- **Neustart-Hinweis:** Wurden seit dem Start Kernel, Grafiktreiber, systemd,
  glibc oder Firmware aktualisiert, erscheint oben „Neustart empfohlen“.
- **Liste sichern …:** speichert alle installierten Programme als lesbares
  Skript, das sie nach einer Neuinstallation wieder einspielt.
- **Neue Spalten „Größe“ und „Installiert“**, sortierbar. Neuer Filter
  „Installiert: letzte 7 Tage / 30 Tage / Jahr“.
- **Doppelt installierte Programme** (z. B. Repo + Flatpak) werden erkannt:
  „(2×)“ hinter dem Namen, Hinweis in den Details, eigener Filter und Fund im
  Reiter „Aufräumen“.
- **Warum ist das installiert?** Die Details zeigen, welche Pakete ein Paket
  brauchen, und was beim Deinstallieren mit entfernt würde (inkl. Platzgewinn).
- **Startmenü-Einträge bearbeiten, ein- und ausblenden.** Systemeinträge
  bleiben unverändert, die eigene Fassung landet im Benutzerordner und lässt
  sich mit „Original wiederherstellen“ rückgängig machen.
- Seltener gebrauchte Filter (Nur veraltete, Nur ohne Auto-Update, Nur doppelt
  installierte, Abhängigkeiten zeigen) stecken jetzt in der Ausklappliste
  „Weitere Filter“.

## 0.4.2

- Die Häkchen für den Filter „Art“ stecken jetzt in einer **Ausklappliste**
  („Art: 🪟 Apps“), damit die Filterzeile übersichtlicher ist. Das Menü bleibt
  beim Anhaken offen, mehrere Arten lassen sich weiterhin kombinieren.

## 0.4.1

- **Filter „Art“ als Häkchen** (☑ Apps ☐ Befehle ☐ Sonstiges), frei
  kombinierbar. Standard ist jetzt **nur Apps**.
- Der Filter wirkt auch im Reiter **„Startmenü-Einträge“**, der ebenfalls eine
  Spalte „Art“ bekommt.
- Die Filter stehen jetzt in einer **zweiten Zeile** der Werkzeugleiste, damit
  auf normal breiten Bildschirmen nichts mehr hinter dem »-Pfeil verschwindet.

## 0.4.0

- **Neue Spalte „Art“ mit Filter:** Jedes Programm ist als 🪟 App (mit Fenster),
  ⌨ Befehl (fürs Terminal) oder 📦 Sonstiges (nicht startbar: Schriftarten,
  Treiber, Firmware, Bibliotheken, Designs, Sammelpakete) eingeordnet.
  Standardmäßig zeigt die Liste nur **Apps + Befehle**, also alles, was man als
  Benutzer starten kann. Die Art steht auch in der Detailansicht und in der
  Textausgabe (`--cli`, `--json`).
- Homebrew-Formeln ohne eigenes Programm (Bibliotheken) gelten nicht mehr
  fälschlich als Befehl.

## 0.3.2

- **Kein falsches „Programm fehlt“ mehr bei Hintergrunddiensten:** Einträge
  wie KDEs „KIO“ (`Exec=kiod6`) rufen Programme auf, die nicht im normalen
  Suchpfad liegen, sondern z. B. unter `/usr/lib/kf6/`. Der Software-Kompass
  kennt jetzt alle solchen Hilfsprogramme aus den Dateilisten von pacman und
  meldet sie nicht mehr als fehlend.

## 0.3.1

- **Aufräumen → „Kaputte Startmenü-Einträge“:** Versteckte Systemeinträge
  (z. B. KDE-Hintergrunddienste wie „KIO“) werden nicht mehr gemeldet. Man
  sieht sie weder im Startmenü, noch kann man sie entfernen. Bei sichtbaren
  Systemeinträgen steht jetzt dabei, welches Programm fehlt.

## 0.3.0

- **Neuer Reiter „Aufräumen“:** findet verwaiste Pakete, alte Versionen im
  Paket-Zwischenspeicher, AUR-Bauordner, unbenutzte Flatpak-Laufzeiten, kaputte
  Startmenü-Einträge und Pakete, die nicht mehr im AUR stehen. Zeigt an, wie
  viel Platz sich gewinnen lässt. Aufgeräumt wird nur nach Rückfrage und
  sichtbar in einem Terminalfenster. Bei Paketen, die nicht mehr im AUR stehen,
  gibt es bewusst keinen Knopf.
- Die Paketgröße aus pacman wird jetzt mit eingelesen.

## 0.2.2

- **KDE-Hilfseinträge werden zugeordnet und erklärt:** Einträge wie
  `userapp-Thunderbird-XXXX.desktop`, die KDE bei „Öffnen mit …“ anlegt, zeigen
  oft auf den echten Programmpfad (z. B. `/usr/lib/thunderbird/thunderbird`
  statt `/usr/bin/thunderbird`). Sie werden jetzt dem richtigen Programm
  zugeordnet, und ein Hinweis erklärt, woher sie stammen. Das gilt auch für
  Steam-Verknüpfungen.

## 0.2.1

- **Keine falschen „Programm fehlt“-Meldungen mehr** im Reiter
  „Startmenü-Einträge“. Einträge wie `wine start …` (Wine), `steam steam://…`
  (Steam-Spiele) oder `flatpak run …` (alle Flatpaks) wurden fälschlich als
  kaputt angezeigt, weil das Wort nach dem Starter für ein Programm gehalten
  wurde.
- Der Tooltip in der Spalte „Startbefehl“ nennt jetzt, welches Programm fehlt.

## 0.2.0

- **Paketverwaltungen einstufen:** Jedes Werkzeug ist als „empfohlen“, „bei
  Bedarf“ oder „nicht empfohlen“ eingestuft, mit Begründung.
- **Empfohlene Werkzeuge nachinstallieren:** nur aus den offiziellen
  Paketquellen und sichtbar in einem Terminalfenster, in dem du selbst dein
  Passwort eingibst.
- **Suche in allen Reitern:** durchsucht auch die Namen von Startmenü-Einträgen,
  Befehle und Pfade.
- **Startmenü-Einträge besser zuordnen:** Einträge wie `konsole -e claude`
  gehören jetzt zum eigentlichen Programm. npm-Programme kennen ihre Befehle.
- **Eigene Symbole:** Bilder werden in den eigenen Symbolordner kopiert, andere
  Formate (JPG, ICO …) automatisch umgewandelt. Der Dialog zeigt, ob ein Symbol
  gefunden wurde.
- **Einträge entfernen:** Alle Einträge im eigenen Benutzerordner lassen sich
  entfernen, fremde nur nach einer Warnung.
- **Weniger Fehlalarme:** Programme von pacman in `/opt` (z. B. TeamSpeak)
  erscheinen nicht mehr zusätzlich als „Manuell“.
- **Brauchbare Löschbefehle** für manuell installierte Programme und AppImages.
- **Versionsanzeige** im Fenstertitel und im Hilfe-Reiter.
- **Deinstallationsbefehl für den Software-Kompass** funktioniert jetzt auch in der
  fish-Shell (Standard unter CachyOS).
- **Lizenz:** GNU GPL v3 oder später.

## 0.1.0

- Erste Version: Programme aus allen gängigen Quellen auflisten, Herkunft
  erklären, Startmenü-Status anzeigen und Einträge anlegen, Update-Prüfung,
  Übersicht der Paketverwaltungen.
