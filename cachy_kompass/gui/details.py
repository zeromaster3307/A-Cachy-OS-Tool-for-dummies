"""HTML-Texte für die Detailansicht und die Hilfe."""

from __future__ import annotations

import shlex
from html import escape

from cachy_kompass import APP_NAME, __version__, desktop, i18n, util
from cachy_kompass.i18n import _, ngettext
from cachy_kompass.installers import InstallerStatus, Rating
from cachy_kompass.models import KIND_INFO, SOURCE_INFO, AutoUpdate, Kind, MenuStatus, Program, Source, UpdateStatus


def _row(label: str, value: str) -> str:
    return f"<tr><td style='padding-right:12px; vertical-align:top'><b>{escape(label)}</b></td><td>{value}</td></tr>"


def _code(text: str) -> str:
    return f"<code style='background-color:rgba(127,127,127,0.18)'>&nbsp;{escape(text)}&nbsp;</code>"


def _names(names: list[str], limit: int = 15) -> str:
    shown = ", ".join(escape(n) for n in names[:limit])
    rest = len(names) - limit
    return shown + (" " + _("… und {n} weitere").format(n=rest) if rest > 0 else "")


def program_html(p: Program, removal: tuple[list[str], str] | None = None, sizes: dict[str, int] | None = None) -> str:
    """Detailansicht. ``removal``: Ergebnis von ``pacman.removal_preview`` (nur bei pacman-Paketen),
    ``sizes``: Paketgrößen, um den Platzgewinn beim Deinstallieren zu zeigen."""
    parts = [f"<h2>{escape(p.display_name)}</h2>"]
    if p.display_name != p.name:
        parts.append(f"<p style='color:gray'>{escape(_('Technischer Name: {name}').format(name=p.name))}</p>")
    if p.description:
        parts.append(f"<p>{escape(p.description)}</p>")
    if p.duplicates:
        others = "".join(
            "<li>" + escape(_("{name} – {source}, Version {version}").format(
                name=d.display_name, source=d.info.label, version=d.version or "?"
            )) + "</li>"
            for d in p.duplicates
        )
        parts.append(
            "<p style='color:#d98a00'>" + _("<b>⚠ Doppelt installiert.</b> Dasselbe Programm gibt es zusätzlich als:") + "</p>"
            f"<ul>{others}</ul><p style='color:gray'>"
            + escape(_(
                "Meist reicht eine Fassung – am besten die aus dem "
                "offiziellen Repo, weil sie mit dem Systemupdate aktuell bleibt. Prüfe aber vorher, ob es "
                "wirklich dasselbe Programm ist (die Erkennung geht nach dem Namen)."
            ))
            + "</p>"
        )

    rows = [_row(_("Version"), escape(p.version or "?"))]
    rows.append(_row(_("Quelle"), escape(p.info.label)))
    rows.append(_row(_("Art"), f"{escape(p.kind.value)} – {escape(KIND_INFO[p.kind])}"))
    if p.origin:
        rows.append(_row(_("Herkunft"), escape(p.origin)))
    if not p.explicit:
        rows.append(_row(_("Grund"), escape(_("Abhängigkeit – wurde automatisch für ein anderes Programm mitinstalliert"))))
    if p.installed_at:
        when = i18n.date_time(p.installed_at)
        if p.installed_approx:
            rows.append(_row(
                _("Installiert"),
                escape(_("ca.") + " " + when) + " <span style='color:gray'>(" + escape(_("Datum der Dateien")) + ")</span>",
            ))
        else:
            rows.append(_row(_("Installiert am"), escape(when)))
    elif p.install_date:
        rows.append(_row(_("Installiert am"), escape(p.install_date)))
    if p.size_bytes:
        rows.append(_row(_("Größe"), escape(util.format_size(p.size_bytes))))
    if p.url:
        rows.append(_row(_("Webseite"), f"<a href='{escape(p.url)}'>{escape(p.url)}</a>"))
    parts.append(f"<table>{''.join(rows)}</table>")

    parts.append(f"<h3>{escape(_('Wie wurde es installiert?'))}</h3>")
    parts.append(f"<p>{escape(p.info.how_installed)}</p>")

    parts.append(f"<h3>{escape(_('Updates'))}</h3>")
    auto = {AutoUpdate.YES: "✔ ", AutoUpdate.PARTIAL: "◐ ", AutoUpdate.NO: "✘ "}[p.info.auto_update]
    parts.append(f"<p>{auto}{escape(p.update_hint())}</p>")
    u = p.update
    if u.status is UpdateStatus.OUTDATED:
        parts.append(
            "<p><b>" + escape(_("⬆ Neuere Version verfügbar: {latest}").format(latest=u.latest)) + "</b> "
            + escape(_("(installiert: {version})").format(version=p.version)) + "</p>"
        )
    elif u.status is UpdateStatus.CURRENT:
        parts.append("<p>" + escape(_("✔ Die installierte Version ist aktuell.")) + "</p>")
    elif u.status is UpdateStatus.NOT_CHECKED:
        parts.append("<p style='color:gray'>" + escape(_("Noch nicht geprüft – klicke oben auf „Nach Updates suchen“.")) + "</p>")
    else:
        parts.append("<p style='color:gray'>" + escape(_("Aktualität: {status}.").format(status=u.status.value)) + "</p>")
    if u.note:
        parts.append(f"<p style='color:gray'>{escape(u.note)}</p>")

    parts.append(f"<h3>{escape(_('Startmenü'))}</h3>")
    status = p.menu_status
    if status is MenuStatus.VISIBLE:
        parts.append("<p>" + escape(_("✔ Das Programm ist über das Startmenü erreichbar.")) + "</p>")
    elif status is MenuStatus.HIDDEN and any(e.hidden_by_user for e in p.desktop_entries):
        parts.append("<p>" + escape(_(
            "◐ Der Eintrag ist ausgeblendet – das hast du selbst so eingestellt. Wieder "
            "einblenden: Reiter „Startmenü-Einträge“ → Eintrag wählen → „Einblenden“ bzw. "
            "„Original wiederherstellen …“."
        )) + "</p>")
    elif status is MenuStatus.HIDDEN:
        parts.append("<p>" + escape(_(
            "◐ Es gibt einen Eintrag, er ist aber absichtlich ausgeblendet "
            "(das ist oft bei Hilfsprogrammen so)."
        )) + "</p>")
    else:
        parts.append("<p>" + escape(_(
            "✘ Kein Startmenü-Eintrag gefunden. Viele Kommandozeilenprogramme und "
            "Hintergrunddienste haben bewusst keinen. Mit dem Knopf unten kannst du "
            "einen eigenen anlegen."
        )) + "</p>")
    if p.desktop_entries:
        items = []
        for e in p.desktop_entries:
            flags = []
            if e.hidden_by_user:
                flags.append(_("von dir ausgeblendet"))
            elif not e.visible:
                flags.append(_("ausgeblendet"))
            if e.created_by_us:
                flags.append(_("vom Software-Kompass angelegt"))
            elif desktop.origin_note(e):
                flags.append(desktop.origin_note(e))
            elif desktop.is_user_entry(e):
                flags.append(_("in deinem Benutzerordner"))
            flag_text = f" <i>({escape(', '.join(flags))})</i>" if flags else ""
            items.append(f"<li>{escape(e.name)}{flag_text}<br><span style='color:gray'>{escape(str(e.path))}</span></li>")
        parts.append(f"<ul>{''.join(items)}</ul>")

    command = desktop.launch_command(p)
    if command and p.kind is not Kind.OTHER:
        parts.append(f"<h3>{escape(_('Starten über das Terminal'))}</h3>")
        if p.menu_status is not MenuStatus.VISIBLE:
            intro = _(
                "Im Terminal (z. B. Konsole) oder über <b>Alt+F2</b> (KRunner) startest du es mit – das klappt "
                "auch, wenn der Startmenü-Eintrag ausgeblendet ist:"
            )
        else:
            intro = _("Im Terminal (z. B. Konsole) oder über <b>Alt+F2</b> (KRunner) startest du es mit:")
        parts.append(f"<p>{intro}<br>{_code(command)}</p>")

    if p.required_by or p.optional_for or not p.explicit:
        parts.append(f"<h3>{escape(_('Warum ist das installiert?'))}</h3>")
        if p.required_by:
            intro = _("Wird gebraucht von:") if p.explicit else _("Mitgebracht von bzw. gebraucht für:")
            parts.append(f"<p>{escape(intro)} <b>{_names(p.required_by)}</b></p>")
        elif not p.explicit:
            parts.append("<p>" + _(
                "Kein installiertes Paket braucht es mehr – es ist <b>verwaist</b> und kann vermutlich "
                "weg (siehe Reiter „Aufräumen“)."
            ) + "</p>")
        if p.optional_for:
            parts.append(f"<p style='color:gray'>{escape(_('Optional genutzt von:'))} {_names(p.optional_for)}</p>")

    if p.executables:
        shown = p.executables[:8]
        rest = len(p.executables) - len(shown)
        more = "<li>" + escape(_("… und {n} weitere").format(n=rest)) + "</li>" if rest > 0 else ""
        parts.append(f"<h3>{escape(_('Programmdateien'))}</h3>")
        parts.append("<ul>" + "".join(f"<li>{escape(x)}</li>" for x in shown) + more + "</ul>")

    parts.append(f"<h3>{escape(_('Deinstallieren'))}</h3>")
    if removal is not None:
        names, error = removal
        if error:
            parts.append(
                "<p style='color:#d64545'><b>" + escape(_("✘ Nicht ohne Weiteres entfernbar.")) + f"</b> {escape(error)}</p>"
            )
        elif names:
            others = [n for n in names if n != p.name]
            freed = sum((sizes or {}).get(n, 0) for n in names)
            if others:
                text = _("Würde zusammen mit diesen nicht mehr benötigten Abhängigkeiten entfernt:") + " "
            else:
                text = _("Würde allein entfernt – keine weiteren Pakete betroffen.")
            parts.append(f"<p>{escape(text)}{_names(others)}</p>")
            if freed:
                parts.append("<p>" + _("Platzgewinn: ca. <b>{size}</b>").format(size=escape(util.format_size(freed))) + "</p>")
    parts.append(
        "<p>" + escape(_("Zum Entfernen diesen Befehl in ein Terminal (z. B. Konsole) kopieren:")) + "<br>"
        f"{_code(p.uninstall_command())}</p>"
        + (
            "<p>" + _(
                "<b>Achtung:</b> Prüfe vorher, ob du das Programm wirklich nicht mehr brauchst. "
                "Manche von Hand installierten Programme bringen ein eigenes Deinstallationsskript "
                "mit, das zusätzlich Einstellungen und Startmenü-Einträge aufräumt."
            ) + "</p>"
            if p.source is Source.MANUAL and not p.uninstall_override
            else ""
        )
        + "<p style='color:gray'>" + escape(_(
            "Der Software-Kompass löscht selbst keine Programme – so kann nichts aus Versehen kaputtgehen."
        )) + "</p>"
    )
    return "".join(parts)


def help_html() -> str:
    sources = "".join(
        f"<tr><td style='padding-right:12px; vertical-align:top'><b>{escape(info.label)}</b></td>"
        f"<td>{escape(info.how_installed)}<br><i>{escape(info.update_hint.format(name='…'))}</i></td></tr>"
        for info in SOURCE_INFO.values()
    )
    version = escape(_("{app} – Version {version}").format(app=APP_NAME, version=__version__))
    intro = _(
        "<h2>Kurze Erklärung</h2>\n"
        "<p>Dieses Programm zeigt dir, <b>welche Programme installiert sind</b>, <b>woher sie\n"
        "stammen</b>, ob sie im <b>Startmenü</b> auftauchen und ob sie beim normalen\n"
        "<b>Systemupdate</b> mit aktualisiert werden.</p>"
    )
    columns = _(
        "<h3>Die Spalten</h3>\n"
        "<ul>\n"
        "<li><b>Quelle</b> – über welchen Weg das Programm installiert wurde (siehe unten).</li>\n"
        "<li><b>Startmenü</b> – ✔ sichtbar, ◐ Eintrag vorhanden aber ausgeblendet, ✘ kein Eintrag.</li>\n"
        "<li><b>Auto-Update</b> – ✔ wird beim Systemupdate mitaktualisiert, ◐ nur mit dem\n"
        "richtigen Werkzeug, ✘ musst du selbst aktualisieren.</li>\n"
        "<li><b>Aktuell?</b> – erst nach Klick auf „Nach Updates suchen“: ✔ aktuell,\n"
        "⬆ neuere Version verfügbar.</li>\n"
        "<li><b>Größe</b> – belegter Speicherplatz.</li>\n"
        "<li><b>Installiert</b> – wann das Programm installiert wurde. „ca.“ heißt: Datum der\n"
        "Programmdateien (bei Flatpak, AppImage usw. gibt es kein Protokoll).</li>\n"
        "<li><b>(2×)</b> hinter dem Namen – das Programm ist doppelt installiert, z. B. aus dem\n"
        "Repo und als Flatpak.</li>\n"
        "</ul>"
    )
    important = _(
        "<h3>Wichtig zu wissen</h3>\n"
        "<ul>\n"
        "<li>Standardmäßig werden nur Programme gezeigt, die <b>bewusst installiert</b>\n"
        "wurden. Bibliotheken und Abhängigkeiten blendest du mit dem Häkchen\n"
        "„Abhängigkeiten zeigen“ ein.</li>\n"
        "<li>Der Software-Kompass <b>bekommt nie selbst Administratorrechte</b>. Selbst legt er\n"
        "nur Startmenü-Einträge (und deren Symbole) in deinem Benutzerordner an\n"
        "(<code>~/.local/share/applications</code>). Löschen kann er nur Einträge aus deinem\n"
        "Benutzerordner – nach Rückfrage, Systemeinträge nie. Alles andere (Aufräumen,\n"
        "Updates, Nachinstallieren) läuft nur auf deinen Klick sichtbar in einem\n"
        "Terminalfenster, in dem du selbst dein Passwort eingibst.</li>\n"
        "<li>Im Reiter <b>„Aufräumen“</b> findest du verwaiste Pakete, alte Paketversionen\n"
        "und andere Platzfresser – aufgeräumt wird nur nach Rückfrage, sichtbar im Terminal.</li>\n"
        "<li><b>„Alles aktualisieren …“</b> startet das Systemupdate (Repo und AUR),\n"
        "Flatpak-Updates usw. sichtbar in einem Terminalfenster. Erscheint danach oben der\n"
        "Hinweis <b>„Neustart empfohlen“</b>, wurden z. B. Kernel oder Grafiktreiber erneuert.</li>\n"
        "<li><b>„Liste sichern …“</b> speichert alle installierten Programme als Skript. Damit\n"
        "spielst du sie nach einer Neuinstallation mit <code>bash programme-….sh</code> wieder ein.</li>\n"
        "<li>Im Reiter <b>„Startmenü-Einträge“</b> kannst du Einträge bearbeiten sowie ein- und\n"
        "ausblenden. Systemeinträge bleiben dabei unverändert – deine Fassung landet im\n"
        "Benutzerordner und lässt sich mit „Original wiederherstellen“ rückgängig machen.</li>\n"
        "</ul>"
    )
    sources_title = escape(_("Die Installationsquellen"))
    return f"""
<p style='color:gray'>{version}</p>
{intro}

{columns}

{important}

<h3>{sources_title}</h3>
<table cellspacing="6">{sources}</table>
"""


def installer_html(status: InstallerStatus) -> str:
    """Detailansicht für eine Paketverwaltung bzw. ein Werkzeug."""
    spec = status.spec
    parts = [f"<h2>{escape(spec.name)}</h2>", f"<p>{escape(spec.description)}</p>"]
    parts.append(
        "<h3>" + escape(_("Einstufung: {rating}").format(rating=spec.rating.value)) + f"</h3><p>{escape(spec.reason)}</p>"
    )
    if status.present:
        parts.append("<h3>" + escape(_("Status")) + "</h3><p>" + escape(_("✔ Auf diesem System vorhanden")))
        if status.found_via:
            parts.append(
                " <span style='color:gray'>(" + escape(_("gefunden über: {what}").format(what=", ".join(status.found_via))) + ")</span>"
            )
        parts.append(".</p>")
        if status.program_count:
            parts.append("<p>" + ngettext(
                "Darüber ist <b>{n} Programm</b> installiert. Würdest du {tool} entfernen, wäre es nicht mehr "
                "nutzbar bzw. nicht mehr aktualisierbar.",
                "Darüber sind <b>{n} Programme</b> installiert. Würdest du {tool} entfernen, wären diese "
                "Programme nicht mehr nutzbar bzw. nicht mehr aktualisierbar.",
                status.program_count,
            ).format(n=status.program_count, tool=escape(spec.name)) + "</p>")
        if status.uninstall_command and spec.rating is not Rating.BASE:
            parts.append(
                "<p style='color:gray'>"
                + escape(_("Der Software-Kompass entfernt keine Paketverwaltungen. Falls du es wirklich willst, ginge es mit:"))
                + f"<br>{_code(status.uninstall_command)}</p>"
            )
        return "".join(parts)

    parts.append("<h3>" + escape(_("Installieren")) + "</h3>")
    if status.install_command:
        parts.append(
            f"<p>{escape(status.install_note)} " + escape(_("Befehl:")) + f"<br>{_code(shlex.join(status.install_command))}</p>"
        )
        parts.append("<p>" + escape(_("Klicke auf „Installieren …“ – der Befehl läuft dann sichtbar in einem Terminalfenster.")) + "</p>")
        if spec.after_install:
            parts.append("<p><b>" + escape(_("Danach:")) + f"</b> {escape(spec.after_install)}</p>")
    else:
        note = status.install_note or _("Wird nicht zur Installation angeboten.")
        parts.append(f"<p style='color:gray'>{escape(note)}</p>")
    return "".join(parts)
