"""Dialog „Alles aktualisieren“: Update-Schritte auswählen und sichtbar im Terminal starten."""

from __future__ import annotations

from html import escape

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from cachy_kompass import terminal, update_all
from cachy_kompass.models import Program


class UpdateAllDialog(QDialog):
    def __init__(self, programs: list[Program], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Alles aktualisieren")
        self.setMinimumWidth(560)
        self.steps = update_all.plan(programs)

        intro = QLabel(
            "Diese Updates werden nacheinander in einem Terminalfenster ausgeführt. Dort siehst du "
            "genau, was passiert, gibst – falls nötig – dein Passwort ein und bestätigst die "
            "Installation. Tipp: Vor einem großen Update laufende Programme speichern."
        )
        intro.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(intro)

        self.boxes: list[tuple[QCheckBox, update_all.UpdateStep]] = []
        for step in self.steps:
            box = QCheckBox(step.label)
            box.setChecked(step.default)
            box.setToolTip(terminal.describe(step.command))
            hint = QLabel(f"{escape(step.explanation)}<br><code>{escape(terminal.describe(step.command))}</code>")
            hint.setWordWrap(True)
            hint.setStyleSheet("color: gray; margin-left: 22px; margin-bottom: 6px")
            layout.addWidget(box)
            layout.addWidget(hint)
            box.toggled.connect(self._update_ok)
            self.boxes.append((box, step))

        if not self.steps:
            layout.addWidget(QLabel("Es wurde kein passendes Update-Werkzeug gefunden."))

        notes = update_all.not_covered(programs, self.steps)
        if notes:
            extra = QLabel("<b>Nicht dabei:</b><ul>" + "".join(f"<li>{escape(n)}</li>" for n in notes) + "</ul>")
            extra.setWordWrap(True)
            layout.addWidget(extra)

        after = QLabel(
            "Danach im Software-Kompass auf „Neu einlesen“ klicken. Wurde der Kernel oder der "
            "Grafiktreiber aktualisiert, erscheint oben ein Hinweis, dass ein Neustart fällig ist."
        )
        after.setWordWrap(True)
        after.setStyleSheet("color: gray")
        layout.addWidget(after)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Terminal öffnen")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._update_ok()

    def selected_commands(self) -> list[list[str]]:
        return [step.command for box, step in self.boxes if box.isChecked()]

    def _update_ok(self, _checked: bool = False) -> None:
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(self.selected_commands()))
