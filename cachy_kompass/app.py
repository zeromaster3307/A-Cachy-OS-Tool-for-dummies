"""Startpunkt: wertet die Befehlszeile aus und startet Oberfläche oder Textmodus."""

from __future__ import annotations

import argparse
import logging

from cachy_kompass import APP_NAME, __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cachy-kompass",
        description=f"{APP_NAME}: Zeigt installierte Programme, ihre Herkunft und ihren Startmenü-Status.",
    )
    parser.add_argument("--cli", action="store_true", help="Ergebnis als Text im Terminal statt mit Oberfläche")
    parser.add_argument("--json", action="store_true", help="Ergebnis als JSON ausgeben (setzt --cli voraus)")
    parser.add_argument("--all", action="store_true", help="Auch Abhängigkeiten und Bibliotheken anzeigen")
    parser.add_argument("--updates", action="store_true", help="Zusätzlich nach Updates suchen (braucht Internet)")
    parser.add_argument("--installers", action="store_true", help="Gefundene Paketverwaltungen auflisten")
    parser.add_argument("-v", "--verbose", action="store_true", help="Ausführliche Meldungen zur Fehlersuche")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s: %(message)s")

    if args.cli or args.json:
        from cachy_kompass.cli import run_cli

        return run_cli(args.all, args.updates, args.json, args.installers)

    try:
        from cachy_kompass.gui.main_window import run_gui
    except ImportError as exc:
        print(
            "Die grafische Oberfläche braucht PySide6.\n"
            "Installieren mit:  sudo pacman -S pyside6\n"
            f"(Fehler: {exc})\n"
            "Alternativ ohne Oberfläche:  cachy-kompass --cli"
        )
        return 1
    return run_gui()
