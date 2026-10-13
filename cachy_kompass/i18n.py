"""Übersetzungen: Deutsch ist die Grundsprache, Englisch kommt aus ``locale/en.po``.

Alle Texte stehen auf Deutsch im Code und werden mit ``_()`` (bzw. ``ngettext()``
für Ein-/Mehrzahl) markiert. Die Sprache wird einmal beim Start festgelegt –
bevor die übrigen Module geladen werden –, deshalb dürfen auch Texte, die schon
beim Laden eines Moduls entstehen (z. B. Tabellen mit Erklärungen), ``_()`` nutzen.

Sprachwahl, erste Angabe gewinnt:
  1. ``--lang`` beim Start bzw. ``CACHY_KOMPASS_LANG``
  2. die Systemsprache (``LANGUAGE``, ``LC_ALL``, ``LC_MESSAGES``, ``LANG``)
Gibt es für die gewünschte Sprache keine Übersetzung, bleibt es bei Deutsch.

Die .po-Datei wird direkt eingelesen (kein Übersetzen mit „msgfmt“ nötig), damit
``install.sh`` einfach bleibt.
"""

from __future__ import annotations

import ast
import os
from datetime import datetime
from pathlib import Path

LOCALE_DIR = Path(__file__).parent / "locale"
BASE_LANGUAGE = "de"
ENV_VAR = "CACHY_KOMPASS_LANG"

_language = BASE_LANGUAGE
_catalog: dict[str, str] = {}
_plurals: dict[str, tuple[str, str]] = {}


def available_languages() -> list[str]:
    return [BASE_LANGUAGE] + sorted(p.stem for p in LOCALE_DIR.glob("*.po"))


def system_language() -> str:
    """Sprache aus der Umgebung, z. B. „en“ aus „en_US.UTF-8“ (leer, wenn unbekannt)."""
    for var in (ENV_VAR, "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        # LANGUAGE kann eine Liste sein („en_GB:de“) – die erste Angabe zählt.
        value = value.split(":")[0].split(".")[0].split("@")[0].split("_")[0].lower()
        if value and value not in ("c", "posix"):
            return value
    return ""


def setup(language: str | None = None) -> str:
    """Legt die Sprache fest und lädt die Übersetzung. Gibt die gewählte Sprache zurück."""
    global _language, _catalog, _plurals
    wanted = (language or system_language() or BASE_LANGUAGE).lower().split("_")[0]
    _catalog, _plurals = {}, {}
    _language = BASE_LANGUAGE
    po = LOCALE_DIR / f"{wanted}.po"
    if wanted != BASE_LANGUAGE and po.is_file():
        _catalog, _plurals = parse_po(po.read_text(encoding="utf-8"))
        _language = wanted
    return _language


def language() -> str:
    return _language


def _(text: str) -> str:
    """Übersetzt einen Text. Fehlt die Übersetzung, bleibt er deutsch."""
    return _catalog.get(text) or text


def ngettext(singular: str, plural: str, n: int) -> str:
    """Ein- oder Mehrzahl, übersetzt (Deutsch und Englisch haben dieselbe Regel)."""
    translated = _plurals.get(singular)
    if translated:
        singular, plural = translated
    return singular if n == 1 else plural


# --- Zahlen und Datum ------------------------------------------------------------


def decimal(text: str) -> str:
    """„1.2“ (wie Python schreibt) → „1,2“ auf Deutsch, auf Englisch unverändert."""
    return text if _language == "en" else text.replace(".", ",")


def date(value: datetime) -> str:
    return value.strftime("%Y-%m-%d" if _language == "en" else "%d.%m.%Y")


def date_time(value: datetime) -> str:
    """Datum mit Uhrzeit, z. B. „29.08.2025, 09:29 Uhr“ bzw. „2025-08-29, 09:29“."""
    return value.strftime("%Y-%m-%d, %H:%M" if _language == "en" else "%d.%m.%Y, %H:%M Uhr")


# --- .po-Dateien -----------------------------------------------------------------


def _unquote(line: str) -> str:
    return ast.literal_eval(line)


def parse_po(text: str) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    """Liest eine .po-Datei: (Einzeltexte, Ein-/Mehrzahl-Paare je Einzahl-Text).

    Unterstützt, was ``tools/i18n.py`` schreibt: msgid, msgid_plural, msgstr,
    msgstr[0]/[1], mehrzeilige Texte, Kommentare. Leere Übersetzungen und als
    „fuzzy“ markierte Einträge werden übergangen.
    """
    catalog: dict[str, str] = {}
    plurals: dict[str, tuple[str, str]] = {}
    for entry in iter_po_entries(text):
        if entry.get("fuzzy") or not entry.get("msgid"):
            continue
        if "msgid_plural" in entry:
            one, many = entry.get("msgstr[0]", ""), entry.get("msgstr[1]", "")
            if one and many:
                plurals[entry["msgid"]] = (one, many)
        elif entry.get("msgstr"):
            catalog[entry["msgid"]] = entry["msgstr"]
    return catalog, plurals


def iter_po_entries(text: str):
    """Zerlegt eine .po-Datei in Einträge (dicts mit msgid, msgstr …, Kommentaren)."""
    entry: dict = {}
    key = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if entry:
                yield entry
            entry, key = {}, ""
            continue
        if line.startswith("#"):
            if line.startswith("#,") and "fuzzy" in line:
                entry["fuzzy"] = True
            elif line.startswith("#:"):
                entry.setdefault("refs", []).append(line[2:].strip())
            continue
        if line.startswith('"'):
            if key:
                entry[key] += _unquote(line)
            continue
        key, _sep, rest = line.partition(" ")
        entry[key] = _unquote(rest)
    if entry:
        yield entry


def po_quote(text: str) -> str:
    """Text als .po-Zeichenkette (bei Zeilenumbrüchen mehrzeilig)."""
    def q(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'

    if "\n" not in text.rstrip("\n"):
        return q(text)
    parts = text.splitlines(keepends=True)
    return '""\n' + "\n".join(q(p) for p in parts)


setup(os.environ.get(ENV_VAR))
