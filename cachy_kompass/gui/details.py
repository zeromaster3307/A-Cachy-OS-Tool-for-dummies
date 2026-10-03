"""HTML-Texte für die Detailansicht und die Hilfe."""

from __future__ import annotations

import shlex
from html import escape

from cachy_kompass import APP_NAME, __version__, desktop, util
from cachy_kompass.installers import InstallerStatus, Rating
from cachy_kompass.models import KIND_INFO, SOURCE_INFO, AutoUpdate, MenuStatus, Program, Source, UpdateStatus


def _row(label: str, value: str) -> str:
    return f"<tr><td style='padding-right:12px; vertical-align:top'><b>{escape(label)}</b></td><td>{value}</td></tr>"


def _code(text: str) -> str:
    return f"<code style='background-color:rgba(127,127,127,0.18)'>&nbsp;{escape(text)}&nbsp;</code>"


def _names(names: list[str], limit: int = 15) -> str:
    shown = ", ".join(escape(n) for n in names[:limit])
    return shown + (f" … und {len(names) - limit} weitere" if len(names) > limit else "")


def program_html(p: Program, removal: tuple[list[str], str] | None = None, sizes: dict[str, int] | None = None) -> str:
    """Detailansicht. ``removal``: Ergebnis von ``pacman.removal_preview`` (nur bei pacman-Paketen),
    ``sizes``: Paketgrößen, um den Platzgewinn beim Deinstallieren zu zeigen."""
    parts = [f"<h2>{escape(p.display_name)}</h2>"]
    if p.display_name != p.name:
        parts.append(f"<p style='color:gray'>Technischer Name: {escape(p.name)}</p>")
    if p.description:
        parts.append(f"<p>{escape(p.description)}</p>")
    if p.duplicates:
        others = "".join(
            f"<li>{escape(d.display_name)} – {escape(d.info.label)}, Version {escape(d.version or '?')}</li>"
            for d in p.duplicates
        )
        parts.append(
            "<p style='color:#d98a00'><b>⚠ Doppelt installiert.</b> Dasselbe Programm gibt es zusätzlich als:</p>"
            f"<ul>{others}</ul><p style='color:gray'>Meist reicht eine Fassung – am besten die aus dem "
            "offiziellen Repo, weil sie mit dem Systemupdate aktuell bleibt. Prüfe aber vorher, ob es "
            "wirklich dasselbe Programm ist (die Erkennung geht nach dem Namen).</p>"
        )

    rows = [_row("Version", escape(p.version or "?"))]
    rows.append(_row("Quelle", escape(p.info.label)))
    rows.append(_row("Art", f"{escape(p.kind.value)} – {escape(KIND_INFO[p.kind])}"))
    if p.origin:
        rows.append(_row("Herkunft", escape(p.origin)))
    if not p.explicit:
        rows.append(_row("Grund", "Abhängigkeit – wurde automatisch für ein anderes Programm mitinstalliert"))
    if p.installed_at:
        when = p.installed_at.strftime("%d.%m.%Y, %H:%M Uhr")
        if p.installed_approx:
            rows.append(_row("Installiert", f"ca. {escape(when)} <span style='color:gray'>(Datum der Dateien)</span>"))
        else:
            rows.append(_row("Installiert am", escape(when)))
    elif p.install_date:
        rows.append(_row("Installiert am", escape(p.install_date)))
    if p.size_bytes:
        rows.append(_row("Größe", escape(util.format_size(p.size_bytes))))
    if p.url:
        rows.append(_row("Webseite", f"<a href='{escape(p.url)}'>{escape(p.url)}</a>"))
    parts.append(f"<table>{''.join(rows)}</table>")

    parts.append("<h3>Wie wurde es installiert?</h3>")
    parts.append(f"<p>{escape(p.info.how_installed)}</p>")

    parts.append("<h3>Updates</h3>")
    auto = {AutoUpdate.YES: "✔ ", AutoUpdate.PARTIAL: "◐ ", AutoUpdate.NO: "✘ "}[p.info.auto_update]
    parts.append(f"<p>{auto}{escape(p.update_hint())}</p>")
    u = p.update
    if u.status is UpdateStatus.OUTDATED:
        parts.append(f"<p><b>⬆ Neuere Version verfügbar: {escape(u.latest)}</b> (installiert: {escape(p.version)})</p>")
    elif u.status is UpdateStatus.CURRENT:
        parts.append("<p>✔ Die installierte Version ist aktuell.</p>")
    elif u.status is UpdateStatus.NOT_CHECKED:
        parts.append("<p style='color:gray'>Noch nicht geprüft – klicke oben auf „Nach Updates suchen“.</p>")
    else:
        parts.append(f"<p style='color:gray'>Aktualität: {escape(u.status.value)}.</p>")
    if u.note:
        parts.append(f"<p style='color:gray'>{escape(u.note)}</p>")

    parts.append("<h3>Startmenü</h3>")
    status = p.menu_status
    if status is MenuStatus.VISIBLE:
        parts.append("<p>✔ Das Programm ist über das Startmenü erreichbar.</p>")
    elif status is MenuStatus.HIDDEN and any(e.hidden_by_user for e in p.desktop_entries):
        parts.append(
            "<p>◐ Der Eintrag ist ausgeblendet – das hast du selbst so eingestellt. Wieder "
            "einblenden: Reiter „Startmenü-Einträge“ → Eintrag wählen → „Einblenden“ bzw. "
            "„Original wiederherstellen …“.</p>"
        )
    elif status is MenuStatus.HIDDEN:
        parts.append(
            "<p>◐ Es gibt einen Eintrag, er ist aber absichtlich ausgeblendet "
            "(das ist oft bei Hilfsprogrammen so).</p>"
        )
    else:
        parts.append(
            "<p>✘ Kein Startmenü-Eintrag gefunden. Viele Kommandozeilenprogramme und "
            "Hintergrunddienste haben bewusst keinen. Mit dem Knopf unten kannst du "
            "einen eigenen anlegen.</p>"
        )
    if p.desktop_entries:
        items = []
        for e in p.desktop_entries:
            flags = []
            if e.hidden_by_user:
                flags.append("von dir ausgeblendet")
            elif not e.visible:
                flags.append("ausgeblendet")
            if e.created_by_us:
                flags.append("vom Software-Kompass angelegt")
            elif desktop.origin_note(e):
                flags.append(desktop.origin_note(e))
            elif desktop.is_user_entry(e):
                flags.append("in deinem Benutzerordner")
            flag_text = f" <i>({', '.join(flags)})</i>" if flags else ""
            items.append(f"<li>{escape(e.name)}{flag_text}<br><span style='color:gray'>{escape(str(e.path))}</span></li>")
        parts.append(f"<ul>{''.join(items)}</ul>")

    if p.required_by or p.optional_for or not p.explicit:
        parts.append("<h3>Warum ist das installiert?</h3>")
        if p.required_by:
            intro = "Wird gebraucht von" if p.explicit else "Mitgebracht von bzw. gebraucht für"
            parts.append(f"<p>{intro}: <b>{_names(p.required_by)}</b></p>")
        elif not p.explicit:
            parts.append(
                "<p>Kein installiertes Paket braucht es mehr – es ist <b>verwaist</b> und kann vermutlich "
                "weg (siehe Reiter „Aufräumen“).</p>"
            )
        if p.optional_for:
            parts.append(f"<p style='color:gray'>Optional genutzt von: {_names(p.optional_for)}</p>")

    if p.executables:
        shown = p.executables[:8]
        more = f"<li>… und {len(p.executables) - len(shown)} weitere</li>" if len(p.executables) > len(shown) else ""
        parts.append("<h3>Programmdateien</h3>")
        parts.append("<ul>" + "".join(f"<li>{escape(x)}</li>" for x in shown) + more + "</ul>")

    parts.append("<h3>Deinstallieren</h3>")
    if removal is not None:
        names, error = removal
        if error:
            parts.append(f"<p style='color:#d64545'><b>✘ Nicht ohne Weiteres entfernbar.</b> {escape(error)}</p>")
        elif names:
            others = [n for n in names if n != p.name]
            freed = sum((sizes or {}).get(n, 0) for n in names)
            text = "Würde zusammen mit diesen nicht mehr benötigten Abhängigkeiten entfernt: " if others else "Würde allein entfernt – keine weiteren Pakete betroffen."
            parts.append(f"<p>{text}{_names(others)}</p>")
            if freed:
                parts.append(f"<p>Platzgewinn: ca. <b>{escape(util.format_size(freed))}</b></p>")
    parts.append(
        "<p>Zum Entfernen diesen Befehl in ein Terminal (z. B. Konsole) kopieren:<br>"
        f"{_code(p.uninstall_command())}</p>"
        + (
            "<p><b>Achtung:</b> Prüfe vorher, ob du das Programm wirklich nicht mehr brauchst. "
            "Manche von Hand installierten Programme bringen ein eigenes Deinstallationsskript "
            "mit, das zusätzlich Einstellungen und Startmenü-Einträge aufräumt.</p>"
            if p.source is Source.MANUAL and not p.uninstall_override
            else ""
        )
        + "<p style='color:gray'>Der Software-Kompass löscht selbst keine Programme – "
        "so kann nichts aus Versehen kaputtgehen.</p>"
    )
    return "".join(parts)


def help_html() -> str:
    sources = "".join(
        f"<tr><td style='padding-right:12px; vertical-align:top'><b>{escape(info.label)}</b></td>"
        f"<td>{escape(info.how_installed)}<br><i>{escape(info.update_hint.format(name='…'))}</i></td></tr>"
        for info in SOURCE_INFO.values()
    )
    return f"""
<p style='color:gray'>{escape(APP_NAME)} – Version {escape(__version__)}</p>
<h2>Kurze Erklärung</h2>
<p>Dieses Programm zeigt dir, <b>welche Programme installiert sind</b>, <b>woher sie
stammen</b>, ob sie im <b>Startmenü</b> auftauchen und ob sie beim normalen
<b>Systemupdate</b> mit aktualisiert werden.</p>

<h3>Die Spalten</h3>
<ul>
<li><b>Quelle</b> – über welchen Weg das Programm installiert wurde (siehe unten).</li>
<li><b>Startmenü</b> – ✔ sichtbar, ◐ Eintrag vorhanden aber ausgeblendet, ✘ kein Eintrag.</li>
<li><b>Auto-Update</b> – ✔ wird beim Systemupdate mitaktualisiert, ◐ nur mit dem
richtigen Werkzeug, ✘ musst du selbst aktualisieren.</li>
<li><b>Aktuell?</b> – erst nach Klick auf „Nach Updates suchen“: ✔ aktuell,
⬆ neuere Version verfügbar.</li>
<li><b>Größe</b> – belegter Speicherplatz.</li>
<li><b>Installiert</b> – wann das Programm installiert wurde. „ca.“ heißt: Datum der
Programmdateien (bei Flatpak, AppImage usw. gibt es kein Protokoll).</li>
<li><b>(2×)</b> hinter dem Namen – das Programm ist doppelt installiert, z. B. aus dem
Repo und als Flatpak.</li>
</ul>

<h3>Wichtig zu wissen</h3>
<ul>
<li>Standardmäßig werden nur Programme gezeigt, die <b>bewusst installiert</b>
wurden. Bibliotheken und Abhängigkeiten blendest du mit dem Häkchen
„Abhängigkeiten zeigen“ ein.</li>
<li>Der Software-Kompass <b>verändert nichts am System</b>. Er legt höchstens
Startmenü-Einträge (und deren Symbole) in deinem Benutzerordner an
(<code>~/.local/share/applications</code>). Löschen kann er nur Einträge aus deinem
Benutzerordner – nach Rückfrage, Systemeinträge nie.</li>
<li>Im Reiter <b>„Aufräumen“</b> findest du verwaiste Pakete, alte Paketversionen
und andere Platzfresser – aufgeräumt wird nur nach Rückfrage, sichtbar im Terminal.</li>
<li><b>„Alles aktualisieren …“</b> startet das Systemupdate (Repo und AUR),
Flatpak-Updates usw. sichtbar in einem Terminalfenster. Erscheint danach oben der
Hinweis <b>„Neustart empfohlen“</b>, wurden z. B. Kernel oder Grafiktreiber erneuert.</li>
<li><b>„Liste sichern …“</b> speichert alle installierten Programme als Skript. Damit
spielst du sie nach einer Neuinstallation mit <code>bash programme-….sh</code> wieder ein.</li>
<li>Im Reiter <b>„Startmenü-Einträge“</b> kannst du Einträge bearbeiten sowie ein- und
ausblenden. Systemeinträge bleiben dabei unverändert – deine Fassung landet im
Benutzerordner und lässt sich mit „Original wiederherstellen“ rückgängig machen.</li>
</ul>

<h3>Die Installationsquellen</h3>
<table cellspacing="6">{sources}</table>
"""


def installer_html(status: InstallerStatus) -> str:
    """Detailansicht für eine Paketverwaltung bzw. ein Werkzeug."""
    spec = status.spec
    parts = [f"<h2>{escape(spec.name)}</h2>", f"<p>{escape(spec.description)}</p>"]
    parts.append(f"<h3>Einstufung: {escape(spec.rating.value)}</h3><p>{escape(spec.reason)}</p>")
    if status.present:
        parts.append("<h3>Status</h3><p>✔ Auf diesem System vorhanden")
        if status.found_via:
            parts.append(f" <span style='color:gray'>(gefunden über: {escape(', '.join(status.found_via))})</span>")
        parts.append(".</p>")
        if status.program_count:
            parts.append(
                f"<p>Darüber sind <b>{status.program_count} Programme</b> installiert. Würdest du "
                f"{escape(spec.name)} entfernen, wären diese Programme nicht mehr nutzbar bzw. "
                "nicht mehr aktualisierbar.</p>"
            )
        if status.uninstall_command and spec.rating is not Rating.BASE:
            parts.append(
                "<p style='color:gray'>Der Software-Kompass entfernt keine Paketverwaltungen. "
                f"Falls du es wirklich willst, ginge es mit:<br>{_code(status.uninstall_command)}</p>"
            )
        return "".join(parts)

    parts.append("<h3>Installieren</h3>")
    if status.install_command:
        parts.append(f"<p>{escape(status.install_note)} Befehl:<br>{_code(shlex.join(status.install_command))}</p>")
        parts.append("<p>Klicke auf „Installieren …“ – der Befehl läuft dann sichtbar in einem Terminalfenster.</p>")
        if spec.after_install:
            parts.append(f"<p><b>Danach:</b> {escape(spec.after_install)}</p>")
    else:
        parts.append(f"<p style='color:gray'>{escape(status.install_note or 'Wird nicht zur Installation angeboten.')}</p>")
    return "".join(parts)
