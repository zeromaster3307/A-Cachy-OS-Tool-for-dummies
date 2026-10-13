#!/usr/bin/env python3
"""Übersetzungsdatei pflegen: Texte aus dem Code sammeln und ``en.po`` abgleichen.

    python tools/i18n.py update   # neue Texte in locale/*.po eintragen, alte entfernen
    python tools/i18n.py check    # fehlende/fehlerhafte Übersetzungen melden (Code 1)

Gesammelt werden alle Aufrufe ``_("…")`` und ``ngettext("…", "…", n)`` mit
festem Text. Vorhandene Übersetzungen bleiben beim Abgleich erhalten.
"""

from __future__ import annotations

import ast
import re
import string
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "cachy_kompass"
sys.path.insert(0, str(ROOT))

from cachy_kompass import i18n  # noqa: E402


@dataclass
class Message:
    msgid: str
    plural: str = ""
    refs: list[str] = field(default_factory=list)


def extract(package: Path = PACKAGE) -> dict[str, Message]:
    """Alle markierten Texte im Paket, in der Reihenfolge ihres ersten Auftretens."""
    messages: dict[str, Message] = {}
    for path in sorted(package.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            args = node.args
            if node.func.id == "_" and len(args) == 1:
                texts = args[:1]
            elif node.func.id == "ngettext" and len(args) == 3:
                texts = args[:2]
            else:
                continue
            if not all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in texts):
                raise SystemExit(f"{path}:{node.lineno}: {node.func.id}() braucht festen Text, keine Variable/f-String")
            msgid = texts[0].value
            msg = messages.setdefault(msgid, Message(msgid, texts[1].value if len(texts) > 1 else ""))
            msg.refs.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    # ast.walk geht nicht in Quelltext-Reihenfolge – nach erster Fundstelle sortieren
    def first_ref(m: Message) -> tuple[str, int]:
        file, line = m.refs[0].rsplit(":", 1)
        return file, int(line)

    return {m.msgid: m for m in sorted(messages.values(), key=first_ref)}


def placeholders(text: str) -> set[str]:
    """Benannte Platzhalter wie {name} (doppelte Klammern {{ }} zählen nicht)."""
    try:
        return {f for _, f, _, _ in string.Formatter().parse(text) if f is not None}
    except ValueError:
        return {"<ungültig>"}


# Nur echte HTML-Tags vergleichen – „<dateiname>“ im Skript-Text ist keins
_HTML_TAG = re.compile(r"</?(a|b|i|p|h[1-6]|ul|ol|li|br|code|span|table|tr|td)\b")


def tags(text: str) -> list[str]:
    return sorted(_HTML_TAG.findall(text))


def write_po(path: Path, messages: dict[str, Message], old_entries: dict[str, dict]) -> None:
    out = [
        "# Englische Übersetzung des Cachy Software-Kompass.",
        "# Gepflegt mit „python tools/i18n.py update“.",
        'msgid ""',
        'msgstr ""',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Language: en\\n"',
        "",
    ]
    for msg in messages.values():
        old = old_entries.get(msg.msgid, {})
        out += [f"#: {' '.join(msg.refs)}"]
        out += [f"msgid {i18n.po_quote(msg.msgid)}"]
        if msg.plural:
            out += [f"msgid_plural {i18n.po_quote(msg.plural)}"]
            out += [f"msgstr[0] {i18n.po_quote(old.get('msgstr[0]', ''))}"]
            out += [f"msgstr[1] {i18n.po_quote(old.get('msgstr[1]', ''))}"]
        else:
            out += [f"msgstr {i18n.po_quote(old.get('msgstr', ''))}"]
        out += [""]
    path.write_text("\n".join(out), encoding="utf-8")


def read_entries(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    return {e["msgid"]: e for e in i18n.iter_po_entries(path.read_text(encoding="utf-8")) if e.get("msgid")}


def problems(messages: dict[str, Message], entries: dict[str, dict]) -> list[str]:
    """Was an einer Übersetzungsdatei nicht stimmt (leer = alles gut)."""
    found = []
    for msg in messages.values():
        entry = entries.get(msg.msgid)
        where = msg.refs[0]
        if entry is None:
            found.append(f"{where}: fehlt in der .po-Datei: {msg.msgid[:60]!r}")
            continue
        pairs = [(msg.msgid, entry.get("msgstr", ""))]
        if msg.plural:
            pairs = [(msg.msgid, entry.get("msgstr[0]", "")), (msg.plural, entry.get("msgstr[1]", ""))]
        for source, translated in pairs:
            if not translated:
                found.append(f"{where}: nicht übersetzt: {source[:60]!r}")
            elif placeholders(source) != placeholders(translated):
                found.append(f"{where}: Platzhalter passen nicht: {sorted(placeholders(source))} ≠ {sorted(placeholders(translated))}")
            elif tags(source) != tags(translated):
                found.append(f"{where}: HTML-Tags passen nicht: {source[:60]!r}")
    for msgid in entries.keys() - messages.keys():
        found.append(f"veraltet (nicht mehr im Code): {msgid[:60]!r}")
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in ("update", "check"):
        print(__doc__)
        return 2
    messages = extract()
    status = 0
    for po in sorted(i18n.LOCALE_DIR.glob("*.po")):
        entries = read_entries(po)
        if argv[0] == "update":
            write_po(po, messages, entries)
            entries = read_entries(po)
        issues = problems(messages, entries)
        print(f"{po.relative_to(ROOT)}: {len(messages)} Texte, {len(issues)} Probleme")
        for issue in issues:
            print("  " + issue)
        status = status or (1 if issues else 0)
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
