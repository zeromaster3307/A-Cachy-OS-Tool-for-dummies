"""Reiter „Aufräumen“: Fundstücke anzeigen, erklären und auf Wunsch aufräumen."""

from __future__ import annotations

from functools import partial
from html import escape
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from cachy_kompass import cleanup, desktop, terminal, util
from cachy_kompass.cleanup import Action, CleanupItem
from cachy_kompass.gui.table_model import GREEN, GREY, ORANGE

if TYPE_CHECKING:
    from cachy_kompass.gui.main_window import MainWindow

MAX_DETAILS = 60


def item_html(item: CleanupItem) -> str:
    parts = [f"<h2>{escape(item.title)}</h2>", f"<p>{escape(item.explanation)}</p>"]
    parts.append(f"<h3>Ergebnis: {escape(item.summary)}</h3>")
    if item.details:
        shown = item.details[:MAX_DETAILS]
        rest = len(item.details) - len(shown)
        parts.append("<ul>" + "".join(f"<li>{escape(d)}</li>" for d in shown) + "</ul>")
        if rest:
            parts.append(f"<p style='color:gray'>… und {rest} weitere.</p>")
    if item.action is Action.TERMINAL:
        parts.append(
            "<p>Klicke auf „Aufräumen …“. Es öffnet sich ein Terminalfenster mit diesen Befehlen:<br>"
            f"<code>{escape(terminal.describe(item.commands))}</code></p>"
        )
    elif item.action is Action.REMOVE_ENTRIES:
        parts.append(f"<p>Klicke auf „Aufräumen …“, um {len(item.entries)} Einträge aus deinem Benutzerordner zu entfernen.</p>")
    if item.warning:
        parts.append(f"<p><b>Gut zu wissen:</b> {escape(item.warning)}</p>")
    if item.manual_command:
        parts.append(
            "<p style='color:gray'>Kein Aufräum-Knopf – falls du es selbst machen willst, ginge es so:<br>"
            f"<code>{escape(item.manual_command)}</code></p>"
        )
    return "".join(parts)


class CleanupTab(QWidget):
    def __init__(self, window: MainWindow) -> None:
        super().__init__()
        self.main = window
        self.items: list[CleanupItem] = []

        info = QLabel(
            "Findet Dinge, die unnötig Platz belegen oder kaputt sind. Das Prüfen verändert nichts. "
            "Aufgeräumt wird nur, wenn du es bestätigst – Befehle mit Administratorrechten laufen "
            "dabei sichtbar in einem Terminalfenster."
        )
        info.setWordWrap(True)
        self.check_button = QPushButton(QIcon.fromTheme("edit-find"), "Jetzt prüfen")
        self.check_button.clicked.connect(self.start_check)
        self.total_label = QLabel()
        top = QHBoxLayout()
        top.addWidget(self.check_button)
        top.addWidget(self.total_label, 1)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Fund", "Ergebnis", "Platz"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 230)
        self.table.setColumnWidth(2, 100)
        self.table.itemSelectionChanged.connect(self._selected)

        self.details = QTextBrowser()
        self.details.setHtml("<p style='color:gray'>Klicke auf „Jetzt prüfen“.</p>")
        self.clean_button = QPushButton(QIcon.fromTheme("edit-clear-all", QIcon.fromTheme("edit-delete")), "Aufräumen …")
        self.clean_button.setEnabled(False)
        self.clean_button.clicked.connect(self._clean_selected)
        self.copy_button = QPushButton(QIcon.fromTheme("edit-copy"), "Befehl kopieren")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self._copy_command)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.details)
        buttons = QHBoxLayout()
        buttons.addWidget(self.clean_button)
        buttons.addWidget(self.copy_button)
        right_layout.addLayout(buttons)

        splitter = QSplitter()
        splitter.addWidget(self.table)
        splitter.addWidget(right)
        splitter.setSizes([700, 600])

        layout = QVBoxLayout(self)
        layout.addWidget(info)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)

    # --- Prüfen --------------------------------------------------------------

    def start_check(self) -> None:
        result = self.main.result
        if result is None or self.main.runner.busy:
            return
        self.check_button.setEnabled(False)
        self.main._set_busy(True)
        self.main.runner.start(
            partial(cleanup.scan, duplicate_groups=result.duplicate_groups),
            result.programs,
            result.entries,
            result.helper_names,
            on_done=self._check_done,
            on_error=self._check_failed,
            on_progress=self.main._status,
        )

    def _check_failed(self, text: str) -> None:
        self.check_button.setEnabled(True)
        self.main._error(text)

    def _check_done(self, items: list[CleanupItem]) -> None:
        self.items = items
        self.check_button.setEnabled(True)
        self.main._set_busy(False)
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            if item.summary in ("nicht prüfbar", "Fehler"):
                color = GREY
            else:
                color = ORANGE if item.found else GREEN
            cells = [item.title, item.summary, util.format_size(item.size) if item.size else ""]
            for col, text in enumerate(cells):
                cell = QTableWidgetItem(text)
                if col == 1:
                    cell.setForeground(color)
                if col == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, row)
                self.table.setItem(row, col, cell)
        total = sum(i.size for i in items)
        self.total_label.setText(
            f"Möglicher Platzgewinn: <b>{util.format_size(total)}</b>" if total else "Nichts Größeres zu holen."
        )
        self.main._status("Aufräum-Prüfung abgeschlossen.")
        if items:
            self.table.selectRow(0)

    # --- Auswahl & Aufräumen -------------------------------------------------

    def _current(self) -> CleanupItem | None:
        rows = self.table.selectionModel().selectedRows()
        return self.items[rows[0].row()] if rows else None

    def _selected(self) -> None:
        item = self._current()
        if item is None:
            return
        self.details.setHtml(item_html(item))
        self.clean_button.setEnabled(item.found and item.action is not Action.NONE)
        self.copy_button.setEnabled(bool(item.commands or item.manual_command))

    def _copy_command(self) -> None:
        item = self._current()
        if item is None:
            return
        text = terminal.describe(item.commands) if item.commands else item.manual_command
        QGuiApplication.clipboard().setText(text)
        self.main._status(f"In die Zwischenablage kopiert: {text}")

    def _confirm(self, item: CleanupItem, what: str) -> bool:
        text = f"{item.title} aufräumen?\n\n{what}"
        if item.warning:
            text += f"\n\n{item.warning}"
        box = QMessageBox(QMessageBox.Icon.Question, "Aufräumen", text, parent=self)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText("Aufräumen")
        box.button(QMessageBox.StandardButton.No).setText("Abbrechen")
        return box.exec() == QMessageBox.StandardButton.Yes

    def _clean_selected(self) -> None:
        item = self._current()
        if item is None:
            return
        if item.action is Action.TERMINAL:
            if not self._confirm(item, f"Es öffnet sich ein Terminalfenster mit:\n\n    {terminal.describe(item.commands)}"):
                return
            if terminal.run_in_terminal(item.commands):
                self.main._status("Terminal geöffnet. Danach auf „Jetzt prüfen“ klicken, um das Ergebnis zu sehen.")
            else:
                QGuiApplication.clipboard().setText(terminal.describe(item.commands))
                QMessageBox.information(
                    self, "Kein Terminal gefunden",
                    "Es wurde kein Terminalprogramm gefunden. Der Befehl liegt in der Zwischenablage.",
                )
        elif item.action is Action.REMOVE_ENTRIES:
            names = "\n".join(f"  • {e.name} ({e.path.name})" for e in item.entries[:20])
            if not self._confirm(item, f"Diese Einträge werden aus deinem Benutzerordner entfernt:\n\n{names}"):
                return
            failed = []
            for entry in item.entries:
                try:
                    desktop.remove_entry(entry)
                except OSError as exc:
                    failed.append(f"{entry.path}: {exc}")
            self.main._rematch()
            if failed:
                QMessageBox.warning(self, "Nicht alles entfernt", "\n".join(failed))
            self.start_check()
