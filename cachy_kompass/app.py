"""Startpunkt: wertet die Befehlszeile aus und startet Oberfläche oder Textmodus."""

from __future__ import annotations

import argparse
import logging
import sys

from cachy_kompass import APP_NAME, __version__, i18n
from cachy_kompass.i18n import _


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cachy-kompass",
        description=_("{app}: Zeigt installierte Programme, ihre Herkunft und ihren Startmenü-Status.").format(app=APP_NAME),
    )
    parser.add_argument("--cli", action="store_true", help=_("Ergebnis als Text im Terminal statt mit Oberfläche"))
    parser.add_argument("--json", action="store_true", help=_("Ergebnis als JSON ausgeben (setzt --cli voraus)"))
    parser.add_argument("--all", action="store_true", help=_("Auch Abhängigkeiten und Bibliotheken anzeigen"))
    parser.add_argument("--updates", action="store_true", help=_("Zusätzlich nach Updates suchen (braucht Internet)"))
    parser.add_argument("--installers", action="store_true", help=_("Gefundene Paketverwaltungen auflisten"))
    parser.add_argument("-v", "--verbose", action="store_true", help=_("Ausführliche Meldungen zur Fehlersuche"))
    parser.add_argument(
        "--lang",
        choices=i18n.available_languages(),
        help=_("Sprache der Oberfläche (Standard: Systemsprache)"),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _requested_language(argv: list[str]) -> str | None:
    """„--lang en“ bzw. „--lang=en“ schon vor dem Aufbau der Hilfe-Texte auslesen."""
    for i, arg in enumerate(argv):
        if arg == "--lang" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--lang="):
            return arg.split("=", 1)[1]
    return None


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    # Die Sprache muss feststehen, bevor Oberfläche und Textmodus geladen werden.
    i18n.setup(_requested_language(argv))
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s: %(message)s")

    if args.cli or args.json:
        from cachy_kompass.cli import run_cli

        return run_cli(args.all, args.updates, args.json, args.installers)

    try:
        from cachy_kompass.gui.main_window import run_gui
    except ImportError as exc:
        print(
            _(
                "Die grafische Oberfläche braucht PySide6.\n"
                "Installieren mit:  sudo pacman -S pyside6\n"
                "(Fehler: {error})\n"
                "Alternativ ohne Oberfläche:  cachy-kompass --cli"
            ).format(error=exc)
        )
        return 1
    return run_gui()
