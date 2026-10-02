"""HTML-Texte für die Detailansicht und die Hilfe."""

from __future__ import annotations

from html import escape

from cachy_kompass.models import SOURCE_INFO, AutoUpdate, MenuStatus, Program, Source, UpdateStatus


def _row(label: str, value: str) -> str:
    return f"<tr><td style='padding-right:12px; vertical-align:top'><b>{escape(label)}</b></td><td>{value}</td></tr>"


def _code(text: str) -> str:
    return f"<code style='background-color:rgba(127,127,127,0.18)'>&nbsp;{escape(text)}&nbsp;</code>"


def program_html(p: Program) -> str:
    parts = [f"<h2>{escape(p.display_name)}</h2>"]
    if p.display_name != p.name:
        parts.append(f"<p style='color:gray'>Technischer Name: {escape(p.name)}</p>")
    if p.description:
        parts.append(f"<p>{escape(p.description)}</p>")

    rows = [_row("Version", escape(p.version or "?"))]
    rows.append(_row("Quelle", escape(p.info.label)))
    if p.origin:
        rows.append(_row("Herkunft", escape(p.origin)))
    if not p.explicit:
        rows.append(_row("Art", "Abhängigkeit – wurde automatisch für ein anderes Programm mitinstalliert"))
    if p.install_date:
        rows.append(_row("Installiert am", escape(p.install_date)))
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
            if not e.visible:
                flags.append("ausgeblendet")
            if e.created_by_us:
                flags.append("vom Software-Kompass angelegt")
            flag_text = f" <i>({', '.join(flags)})</i>" if flags else ""
            items.append(f"<li>{escape(e.name)}{flag_text}<br><span style='color:gray'>{escape(str(e.path))}</span></li>")
        parts.append(f"<ul>{''.join(items)}</ul>")

    if p.executables:
        shown = p.executables[:8]
        more = f"<li>… und {len(p.executables) - len(shown)} weitere</li>" if len(p.executables) > len(shown) else ""
        parts.append("<h3>Programmdateien</h3>")
        parts.append("<ul>" + "".join(f"<li>{escape(x)}</li>" for x in shown) + more + "</ul>")

    parts.append("<h3>Deinstallieren</h3>")
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
</ul>

<h3>Wichtig zu wissen</h3>
<ul>
<li>Standardmäßig werden nur Programme gezeigt, die <b>bewusst installiert</b>
wurden. Bibliotheken und Abhängigkeiten blendest du mit dem Häkchen
„Abhängigkeiten zeigen“ ein.</li>
<li>Der Software-Kompass <b>verändert nichts am System</b>. Er legt höchstens
Startmenü-Einträge in deinem Benutzerordner an
(<code>~/.local/share/applications</code>) – und nur solche kann er auch wieder löschen.</li>
<li>Updates installierst du unter CachyOS am einfachsten mit dem Befehl
<code>paru</code> im Terminal (aktualisiert Repo- und AUR-Pakete) und
<code>flatpak update</code> für Flatpaks.</li>
</ul>

<h3>Die Installationsquellen</h3>
<table cellspacing="6">{sources}</table>
"""
