"""Tests für die Übersetzung (Deutsch im Code, Englisch aus locale/en.po)."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from cachy_kompass import i18n

ROOT = Path(__file__).resolve().parent.parent


def _tool():
    spec = importlib.util.spec_from_file_location("i18n_tool", ROOT / "tools" / "i18n.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # nötig für die Dataclass im Werkzeug
    spec.loader.exec_module(module)
    return module


def test_english_translation_is_complete():
    """Jeder markierte Text hat eine Übersetzung mit denselben Platzhaltern und HTML-Tags."""
    tool = _tool()
    messages = tool.extract()
    assert len(messages) > 400
    for po in i18n.LOCALE_DIR.glob("*.po"):
        assert tool.problems(messages, tool.read_entries(po)) == [], po


def test_po_roundtrip_with_plurals_and_newlines():
    po = (
        'msgid ""\nmsgstr ""\n"Language: en\\n"\n\n'
        '#: x.py:1\nmsgid ""\n"Zeile eins\\n"\n"Zeile „zwei“"\nmsgstr ""\n"Line one\\n"\n"Line “two”"\n\n'
        'msgid "{n} Paket"\nmsgid_plural "{n} Pakete"\nmsgstr[0] "{n} package"\nmsgstr[1] "{n} packages"\n\n'
        '#, fuzzy\nmsgid "Unsicher"\nmsgstr "Unsure"\n'
    )
    catalog, plurals = i18n.parse_po(po)
    assert catalog == {"Zeile eins\nZeile „zwei“": "Line one\nLine “two”"}
    assert plurals == {"{n} Paket": ("{n} package", "{n} packages")}
    assert i18n.po_quote("a\nb") == '""\n"a\\n"\n"b"'


def test_system_language(monkeypatch):
    for var in (i18n.ENV_VAR, "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)
    assert i18n.system_language() == ""
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert i18n.system_language() == "en"
    monkeypatch.setenv("LC_ALL", "C")  # „C“ zählt nicht als Sprache
    assert i18n.system_language() == "en"
    monkeypatch.setenv("LANGUAGE", "de_AT:en")
    assert i18n.system_language() == "de"


def _run_english(code: str) -> str:
    env = dict(os.environ, CACHY_KOMPASS_LANG="en", PYTHONPATH=str(ROOT))
    return subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True, cwd=ROOT).stdout


def test_english_output():
    out = _run_english(
        "from datetime import datetime\n"
        "from cachy_kompass import cleanup, i18n, terminal, util\n"
        "from cachy_kompass.models import Source, SOURCE_INFO, UpdateStatus\n"
        "print(i18n.language())\n"
        "print(SOURCE_INFO[Source.REPO].label, '|', UpdateStatus.OUTDATED.value)\n"
        "print(util.format_size(1288490188), '|', i18n.date(datetime(2026, 10, 3)))\n"
        "print(cleanup.count(3, i18n.ngettext('{n} Paket', '{n} Pakete', 3)))\n"
        "print(terminal.build_script(['true']))\n"
    )
    lines = out.splitlines()
    assert lines[0] == "en"
    assert lines[1] == "Official repo | update available"
    assert lines[2] == "1.2 GB | 2026-10-03"
    assert lines[3] == "3 packages"
    assert "running the following command" in out and "Press Enter" in out


def test_english_terminal_script_runs():
    script = _run_english("from cachy_kompass import terminal; print(terminal.build_script(['false']))")
    out = subprocess.run(["bash", "-c", script], input="\n", capture_output=True, text=True, timeout=10).stdout
    assert "✘ Not successful (code 1)" in out


def test_lang_option_on_command_line():
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    env.pop(i18n.ENV_VAR, None)
    out = subprocess.run(
        [sys.executable, "-m", "cachy_kompass", "--lang", "en", "--help"], env=env, capture_output=True, text=True, check=True
    ).stdout
    assert "Print the result as text" in out
    out = subprocess.run(
        [sys.executable, "-m", "cachy_kompass", "--lang=de", "--help"], env=env, capture_output=True, text=True, check=True
    ).stdout
    assert "Ergebnis als Text" in out


def test_unknown_language_falls_back_to_german():
    assert i18n.setup("fr") == "de"
    assert i18n._("Fehler") == "Fehler"
