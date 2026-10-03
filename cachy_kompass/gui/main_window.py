"""Das Hauptfenster des Software-Kompass."""

from __future__ import annotations

import shlex
import sys

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from cachy_kompass import APP_ID, APP_NAME, __version__, desktop, scanner, terminal
from cachy_kompass.gui import details
from cachy_kompass.gui.cleanup_tab import CleanupTab
from cachy_kompass.gui.entry_dialog import EntryDialog
from cachy_kompass.gui.table_model import (
    COL_DESC,
    COL_NAME,
    GREEN,
    GREY,
    ORANGE,
    PROGRAM_ROLE,
    RED,
    ProgramFilterModel,
    ProgramTableModel,
)
from cachy_kompass.gui.workers import TaskRunner
from cachy_kompass.installers import InstallerStatus, Rating
from cachy_kompass.models import SOURCE_INFO, DesktopEntry, MenuStatus, Program, UpdateStatus

RATING_COLOR = {Rating.BASE: GREY, Rating.RECOMMENDED: GREEN, Rating.OPTIONAL: ORANGE, Rating.DISCOURAGED: RED}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.setWindowIcon(QIcon.fromTheme("system-software-install", QIcon.fromTheme("applications-system")))
        self.resize(1300, 780)

        self.runner = TaskRunner()
        self.result: scanner.ScanResult | None = None
        self.model = ProgramTableModel()
        self.proxy = ProgramFilterModel()
        self.proxy.setSourceModel(self.model)

        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()
        self.start_scan()

    # --- Aufbau --------------------------------------------------------------

    def _build_toolbar(self) -> None:
        bar = QToolBar("Werkzeuge")
        bar.setMovable(False)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(bar)

        self.scan_action = QAction(QIcon.fromTheme("view-refresh"), "Neu einlesen", self)
        self.scan_action.setShortcut(QKeySequence.StandardKey.Refresh)
        self.scan_action.setToolTip("Alle installierten Programme erneut suchen (F5)")
        self.scan_action.triggered.connect(self.start_scan)
        bar.addAction(self.scan_action)

        self.update_action = QAction(QIcon.fromTheme("system-software-update"), "Nach Updates suchen", self)
        self.update_action.setToolTip(
            "Prüft im Internet, ob es neuere Versionen gibt. Es wird nichts installiert."
        )
        self.update_action.triggered.connect(self.start_update_check)
        bar.addAction(self.update_action)
        bar.addSeparator()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Suchen (in allen Reitern) …")
        self.search.setToolTip("Durchsucht Namen, Beschreibungen, Startmenü-Einträge, Befehle und Pfade")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(260)
        self.search.textChanged.connect(self._apply_search)
        bar.addWidget(self.search)

        self.source_filter = QComboBox()
        self.source_filter.addItem("Alle Quellen", None)
        for src, info in SOURCE_INFO.items():
            self.source_filter.addItem(info.label, src)
        self.source_filter.currentIndexChanged.connect(
            lambda: self.proxy.update_filter(source=self.source_filter.currentData())
        )
        bar.addWidget(self.source_filter)

        self.menu_filter = QComboBox()
        self.menu_filter.addItem("Startmenü: egal", None)
        self.menu_filter.addItem("Startmenü: vorhanden", MenuStatus.VISIBLE)
        self.menu_filter.addItem("Startmenü: versteckt", MenuStatus.HIDDEN)
        self.menu_filter.addItem("Startmenü: fehlt", MenuStatus.NONE)
        self.menu_filter.currentIndexChanged.connect(
            lambda: self.proxy.update_filter(menu=self.menu_filter.currentData())
        )
        bar.addWidget(self.menu_filter)

        self.outdated_box = QCheckBox("Nur veraltete")
        self.outdated_box.toggled.connect(lambda on: self.proxy.update_filter(only_outdated=on))
        bar.addWidget(self.outdated_box)

        self.manual_box = QCheckBox("Nur ohne Auto-Update")
        self.manual_box.setToolTip("Programme, die beim normalen Systemupdate nicht (sicher) mitaktualisiert werden")
        self.manual_box.toggled.connect(lambda on: self.proxy.update_filter(only_manual_update=on))
        bar.addWidget(self.manual_box)

        self.deps_box = QCheckBox("Abhängigkeiten zeigen")
        self.deps_box.setToolTip("Auch Bibliotheken und automatisch mitinstallierte Pakete anzeigen")
        self.deps_box.toggled.connect(self._toggle_dependencies)
        bar.addWidget(self.deps_box)

    def _build_tabs(self) -> None:
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_programs_tab(), "Programme")
        self.tabs.addTab(self._build_entries_tab(), "Startmenü-Einträge")
        self.tabs.addTab(self._build_installers_tab(), "Paketverwaltungen")
        self.cleanup_tab = CleanupTab(self)
        self.tabs.addTab(self.cleanup_tab, "Aufräumen")
        help_view = QTextBrowser()
        help_view.setOpenExternalLinks(True)
        help_view.setHtml(details.help_html())
        self.tabs.addTab(help_view, "Hilfe")
        # Zeilenhöhen erst berechnen, wenn die Tabelle sichtbar ist und ihre echte Breite kennt
        self.tabs.currentChanged.connect(lambda _: self.installer_table.resizeRowsToContents())
        self.setCentralWidget(self.tabs)

    def _build_programs_tab(self) -> QWidget:
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(COL_NAME, Qt.SortOrder.AscendingOrder)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(COL_DESC, QHeaderView.ResizeMode.Stretch)
        for col, width in enumerate([200, 110, 120, 100, 100, 120]):
            self.table.setColumnWidth(col, width)
        header.setMinimumSectionSize(60)
        self.table.selectionModel().currentRowChanged.connect(self._show_details)
        self.table.doubleClicked.connect(lambda _: self.create_entry())

        self.details = QTextBrowser()
        self.details.setOpenExternalLinks(True)
        self.details.setHtml("<p style='color:gray'>Wähle links ein Programm aus.</p>")

        self.create_button = QPushButton(QIcon.fromTheme("list-add"), "Startmenü-Eintrag anlegen …")
        self.create_button.clicked.connect(self.create_entry)
        self.remove_button = QPushButton(QIcon.fromTheme("list-remove"), "Eintrag entfernen …")
        self.remove_button.setToolTip("Entfernt einen Startmenü-Eintrag aus deinem Benutzerordner")
        self.remove_button.clicked.connect(self.remove_own_entry)
        self.copy_button = QPushButton(QIcon.fromTheme("edit-copy"), "Deinstallier-Befehl kopieren")
        self.copy_button.clicked.connect(self.copy_uninstall)
        for b in (self.create_button, self.remove_button, self.copy_button):
            b.setEnabled(False)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.details)
        buttons = QHBoxLayout()
        buttons.addWidget(self.create_button)
        buttons.addWidget(self.remove_button)
        right_layout.addLayout(buttons)
        right_layout.addWidget(self.copy_button)

        splitter = QSplitter()
        splitter.addWidget(self.table)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([900, 420])
        return splitter

    def _build_entries_tab(self) -> QWidget:
        info = QLabel(
            "Alle Startmenü-Einträge auf diesem System. „Programm fehlt“ bedeutet: Der Eintrag "
            "zeigt auf ein Programm, das es nicht (mehr) gibt – er ist also vermutlich kaputt."
        )
        info.setWordWrap(True)
        self.entries_table = QTableWidget(0, 5)
        self.entries_table.setHorizontalHeaderLabels(["Name", "Sichtbar", "Gehört zu", "Startbefehl", "Datei"])
        self.entries_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.entries_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.entries_table.setSortingEnabled(True)
        self.entries_table.verticalHeader().setVisible(False)
        self.entries_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        for col, width in enumerate([220, 80, 240, 120]):
            self.entries_table.setColumnWidth(col, width)
        self.entries_table.itemSelectionChanged.connect(self._entry_selected)

        self.entry_remove_button = QPushButton(QIcon.fromTheme("list-remove"), "Ausgewählten Eintrag entfernen …")
        self.entry_remove_button.setEnabled(False)
        self.entry_remove_button.setToolTip(
            "Nur Einträge in deinem Benutzerordner können entfernt werden, Systemeinträge nicht."
        )
        self.entry_remove_button.clicked.connect(self._remove_selected_entry)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(info)
        layout.addWidget(self.entries_table)
        layout.addWidget(self.entry_remove_button, alignment=Qt.AlignmentFlag.AlignRight)
        return widget

    def _build_installers_tab(self) -> QWidget:
        info = QLabel(
            "Welche Paketverwaltungen, App-Stores und Update-Werkzeuge auf diesem System vorhanden "
            "sind – und ob sie unter CachyOS empfehlenswert sind. Viele davon werden durch Anleitungen "
            "aus dem Internet nachinstalliert. Wähle eine Zeile für Details."
        )
        info.setWordWrap(True)
        self.installer_table = QTableWidget(0, 6)
        self.installer_table.setHorizontalHeaderLabels(["Werkzeug", "Art", "Vorhanden", "Programme", "Einstufung", "Erklärung"])
        self.installer_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.installer_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.installer_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.installer_table.verticalHeader().setVisible(False)
        self.installer_table.setWordWrap(True)
        self.installer_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        # Zeilenhöhe an den umbrochenen Text anpassen, sobald sich die Breite ändert
        self.installer_table.horizontalHeader().sectionResized.connect(
            lambda *_: self.installer_table.resizeRowsToContents()
        )
        for col, width in enumerate([190, 150, 80, 80, 130]):
            self.installer_table.setColumnWidth(col, width)
        self.installer_table.itemSelectionChanged.connect(self._installer_selected)

        self.installer_details = QTextBrowser()
        self.installer_details.setHtml("<p style='color:gray'>Wähle links ein Werkzeug aus.</p>")
        self.install_button = QPushButton(QIcon.fromTheme("run-install", QIcon.fromTheme("list-add")), "Installieren …")
        self.install_button.setEnabled(False)
        self.install_button.clicked.connect(self._install_selected)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.installer_details)
        right_layout.addWidget(self.install_button)

        splitter = QSplitter()
        splitter.addWidget(self.installer_table)
        splitter.addWidget(right)
        splitter.setSizes([950, 380])

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(info)
        layout.addWidget(splitter, 1)  # die Tabelle bekommt den ganzen Platz
        return widget

    def _build_statusbar(self) -> None:
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.setMaximumWidth(160)
        self.busy.hide()
        self.statusBar().addPermanentWidget(self.busy)

    # --- Abläufe -------------------------------------------------------------

    def _set_busy(self, busy: bool) -> None:
        self.busy.setVisible(busy)
        self.scan_action.setEnabled(not busy)
        self.update_action.setEnabled(not busy and self.result is not None)
        self.cleanup_tab.check_button.setEnabled(not busy and self.result is not None)

    def _status(self, text: str) -> None:
        self.statusBar().showMessage(text)

    def _error(self, details_text: str) -> None:
        self._set_busy(False)
        self._status("Fehler – Details im Fenster.")
        box = QMessageBox(QMessageBox.Icon.Critical, "Fehler", "Leider ist ein Fehler aufgetreten.", parent=self)
        box.setDetailedText(details_text)
        box.exec()

    def start_scan(self) -> None:
        if self.runner.busy:
            return
        self._set_busy(True)
        self.runner.start(scanner.scan, on_done=self._scan_done, on_error=self._error, on_progress=self._status)

    def _scan_done(self, result: scanner.ScanResult) -> None:
        self.result = result
        self.model.set_programs(result.programs)
        self._fill_entries_table()
        self._fill_installer_table()
        self._set_busy(False)
        visible = sum(p.explicit for p in result.programs)
        no_menu = sum(p.explicit and p.menu_status is MenuStatus.NONE for p in result.programs)
        self._status(
            f"{visible} Programme gefunden ({len(result.programs)} Pakete inkl. Abhängigkeiten), "
            f"{no_menu} davon ohne Startmenü-Eintrag."
        )
        if result.warnings:
            QMessageBox.warning(self, "Nicht alles konnte gelesen werden", "\n".join(result.warnings))

    def start_update_check(self) -> None:
        if self.runner.busy or not self.result:
            return
        # Abhängigkeiten nur mitprüfen, wenn sie auch angezeigt werden.
        programs = [p for p in self.result.programs if p.explicit or self.deps_box.isChecked()]
        self._set_busy(True)
        self.runner.start(
            scanner.check_updates, programs, on_done=self._updates_done, on_error=self._error, on_progress=self._status
        )

    def _updates_done(self, results: dict) -> None:
        assert self.result is not None
        scanner.apply_updates(self.result.programs, results)
        self.model.refresh()
        self._set_busy(False)
        self._show_details(self.table.currentIndex())
        outdated = sum(1 for r in results.values() if r.status is UpdateStatus.OUTDATED)
        self._status(f"Update-Prüfung fertig: {outdated} Programme haben eine neuere Version.")

    def _apply_search(self, _text: str = "") -> None:
        """Filtert alle Reiter gleichzeitig nach dem Suchbegriff."""
        text = self.search.text()
        self.proxy.update_filter(search=text)
        words = text.lower().split()
        for table in (self.entries_table, self.installer_table):
            for row in range(table.rowCount()):
                cells = (table.item(row, col) for col in range(table.columnCount()))
                # Tooltips mit durchsuchen – dort steht z. B. der vollständige Startbefehl
                row_text = " ".join(f"{c.text()} {c.toolTip()}" for c in cells if c is not None).lower()
                table.setRowHidden(row, not all(w in row_text for w in words))

    def _toggle_dependencies(self, on: bool) -> None:
        self.proxy.update_filter(show_dependencies=on)

    # --- Detailansicht -------------------------------------------------------

    def current_program(self) -> Program | None:
        index = self.table.currentIndex()
        return index.data(PROGRAM_ROLE) if index.isValid() else None

    def _show_details(self, index: QModelIndex, _previous: QModelIndex | None = None) -> None:
        program = index.data(PROGRAM_ROLE) if index.isValid() else None
        if program is None:
            for b in (self.create_button, self.remove_button, self.copy_button):
                b.setEnabled(False)
            return
        self.details.setHtml(details.program_html(program))
        self.create_button.setEnabled(True)
        self.remove_button.setEnabled(any(desktop.can_remove(e) for e in program.desktop_entries))
        self.copy_button.setEnabled(True)

    def create_entry(self) -> None:
        program = self.current_program()
        if not program:
            return
        if program.menu_status is MenuStatus.VISIBLE:
            answer = QMessageBox.question(
                self,
                "Schon vorhanden",
                f"„{program.display_name}“ hat bereits einen Startmenü-Eintrag.\n\nTrotzdem einen weiteren anlegen?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        dialog = EntryDialog(program, self)
        if dialog.exec() and dialog.created_path:
            self._status(f"Eintrag angelegt: {dialog.created_path}")
            self._rematch()

    def remove_own_entry(self) -> None:
        program = self.current_program()
        if not program:
            return
        removable = [e for e in program.desktop_entries if desktop.can_remove(e)]
        if not removable:
            return
        entry = removable[0]
        if len(removable) > 1:
            labels = [f"{e.name}  ({e.path.name})" for e in removable]
            choice, ok = QInputDialog.getItem(self, "Eintrag entfernen", "Welcher Eintrag soll entfernt werden?", labels, 0, False)
            if not ok:
                return
            entry = removable[labels.index(choice)]
        if self._confirm_remove(entry):
            self._rematch()

    def _confirm_remove(self, entry: DesktopEntry) -> bool:
        text = f"Den Eintrag „{entry.name}“ wirklich entfernen?\n\n{entry.path}"
        if not entry.created_by_us:
            text += (
                "\n\nAchtung: Diesen Eintrag hat nicht der Software-Kompass angelegt, sondern du selbst "
                "oder ein anderes Programm (z. B. Steam, Gear Lever, AppImageLauncher). "
                "Das Programm selbst bleibt installiert – nur der Menüeintrag verschwindet."
            )
        system = desktop.overridden_system_entry(entry)
        if system:
            text += (
                f"\n\nHinweis: Dieser Eintrag ersetzt einen Systemeintrag ({system}). "
                "Nach dem Entfernen erscheint wieder der ursprüngliche Eintrag des Systems."
            )
        box = QMessageBox(QMessageBox.Icon.Question, "Eintrag entfernen", text, parent=self)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText("Entfernen")
        box.button(QMessageBox.StandardButton.No).setText("Abbrechen")
        if box.exec() != QMessageBox.StandardButton.Yes:
            return False
        try:
            desktop.remove_entry(entry)
        except OSError as exc:
            QMessageBox.critical(self, "Fehler", str(exc))
            return False
        self._status(f"Eintrag entfernt: {entry.path}")
        return True

    def copy_uninstall(self) -> None:
        program = self.current_program()
        if program:
            QGuiApplication.clipboard().setText(program.uninstall_command())
            self._status(f"In die Zwischenablage kopiert: {program.uninstall_command()}")

    def _rematch(self) -> None:
        """Startmenü neu einlesen, ohne alle Pakete erneut abzufragen."""
        if not self.result:
            return
        self.result.entries = desktop.load_entries()
        self.result.unmatched_entries = desktop.match_entries(self.result.programs, self.result.entries)
        self.model.refresh()
        self._fill_entries_table()
        self._show_details(self.table.currentIndex())

    # --- Weitere Tabs --------------------------------------------------------

    def _fill_entries_table(self) -> None:
        assert self.result is not None
        table = self.entries_table
        table.setSortingEnabled(False)
        entries = [e for e in self.result.entries if e.type == "Application"]
        table.setRowCount(len(entries))
        for row, e in enumerate(entries):
            owner = self.result.owner_of(e)
            missing = desktop.missing_program(e.exec, self.result.helper_names)
            exists = not missing
            owner_text = f"{owner.display_name} ({owner.info.label})" if owner else "–"
            cells = [
                (e.name, None),
                ("ja" if e.visible else "nein", GREEN if e.visible else GREY),
                (owner_text, None),
                ("ok" if exists else "Programm fehlt", GREEN if exists else RED),
                (str(e.path), None),
            ]
            for col, (text, color) in enumerate(cells):
                item = QTableWidgetItem(text)
                if color is not None:
                    item.setForeground(color)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, e)
                    if e.created_by_us:
                        item.setToolTip("Vom Software-Kompass angelegt")
                    elif desktop.origin_note(e):
                        item.setToolTip(desktop.origin_note(e))
                    elif desktop.is_user_entry(e):
                        item.setToolTip("Liegt in deinem Benutzerordner (von dir oder einem Programm angelegt)")
                if col == 3:
                    hint = f"Nicht gefunden: {missing}\n" if missing else ""
                    item.setToolTip(f"{hint}Startbefehl: {e.exec}")
                table.setItem(row, col, item)
        table.setSortingEnabled(True)
        self._apply_search()

    def _selected_entry(self) -> DesktopEntry | None:
        rows = self.entries_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.entries_table.item(rows[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _entry_selected(self) -> None:
        entry = self._selected_entry()
        self.entry_remove_button.setEnabled(bool(entry and desktop.can_remove(entry)))

    def _remove_selected_entry(self) -> None:
        entry = self._selected_entry()
        if entry and self._confirm_remove(entry):
            self._rematch()

    def _selected_installer(self) -> InstallerStatus | None:
        rows = self.installer_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.installer_table.item(rows[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _installer_selected(self) -> None:
        status = self._selected_installer()
        self.install_button.setEnabled(bool(status and not status.present and status.install_command))
        if status:
            self.installer_details.setHtml(details.installer_html(status))

    def _install_selected(self) -> None:
        status = self._selected_installer()
        if not status or not status.install_command:
            return
        spec = status.spec
        command = shlex.join(status.install_command)
        text = (
            f"„{spec.name}“ installieren?\n\n{spec.description}\n\n"
            f"Einstufung: {spec.rating.value} – {spec.reason}\n\n"
            f"Es öffnet sich ein Terminalfenster mit diesem Befehl:\n\n    {command}\n\n"
            "Dort siehst du genau, was passiert, und gibst – falls nötig – dein Passwort ein. "
            "Bevor pacman etwas installiert, fragt es noch einmal nach."
        )
        if spec.after_install:
            text += f"\n\nDanach wichtig: {spec.after_install}"
        box = QMessageBox(QMessageBox.Icon.Question, "Installieren", text, parent=self)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText("Terminal öffnen")
        box.button(QMessageBox.StandardButton.No).setText("Abbrechen")
        if box.exec() != QMessageBox.StandardButton.Yes:
            return
        if terminal.run_in_terminal(status.install_command):
            self._status("Terminal geöffnet. Wenn die Installation fertig ist, auf „Neu einlesen“ klicken.")
        else:
            QGuiApplication.clipboard().setText(command)
            QMessageBox.information(
                self,
                "Kein Terminal gefunden",
                f"Es wurde kein Terminalprogramm gefunden. Der Befehl wurde in die Zwischenablage kopiert:\n\n{command}\n\n"
                "Füge ihn in ein Terminal ein und drücke Enter.",
            )

    def _fill_installer_table(self) -> None:
        assert self.result is not None
        table = self.installer_table
        rating_order = list(Rating)
        rows = sorted(self.result.installers, key=lambda s: (not s.present, s.spec.kind, rating_order.index(s.spec.rating)))
        table.setRowCount(len(rows))
        for row, status in enumerate(rows):
            spec = status.spec
            present_text = "✔ ja" if status.present else "–"
            count = "" if status.program_count is None else str(status.program_count)
            cells = [spec.name, spec.kind, present_text, count, spec.rating.value, spec.description]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if not status.present:
                    item.setForeground(GREY)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, status)
                if col == 2:
                    item.setForeground(GREEN if status.present else GREY)
                    if status.found_via:
                        item.setToolTip("Gefunden über: " + ", ".join(status.found_via))
                if col == 4:
                    item.setForeground(RATING_COLOR[spec.rating])
                    item.setToolTip(spec.reason)
                table.setItem(row, col, item)
        if table.isVisible():
            table.resizeRowsToContents()
        self._apply_search()


def run_gui() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(APP_ID)
    window = MainWindow()
    window.show()
    return app.exec()

