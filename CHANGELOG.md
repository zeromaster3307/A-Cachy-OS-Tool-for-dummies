# Änderungen

Hier steht, was sich von Version zu Version geändert hat. Die installierte
Version siehst du im Fenstertitel, im Reiter „Hilfe“ oder mit
`cachy-kompass --version`.

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
