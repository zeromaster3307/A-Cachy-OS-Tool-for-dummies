"""Das Hauptfenster des Software-Kompass."""

from __future__ import annotations

import shlex
import shutil
import socket
import sys
from pathlib import Path

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
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
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from cachy_kompass import APP_ID, APP_NAME, __version__, backup, desktop, scanner, terminal
from cachy_kompass.gui import details
from cachy_kompass.gui.cleanup_tab import CleanupTab
from cachy_kompass.gui.entry_dialog import EntryDialog
from cachy_kompass.gui.table_model import (
    COL_DESC,
    COL_NAME,
    DEFAULT_KINDS,
    GREEN,
    GREY,
    KIND_CHECKBOX_TEXT,
    KIND_TEXT,
    ORANGE,
    PROGRAM_ROLE,
    RED,
    ProgramFilterModel,
    ProgramTableModel,
)
from cachy_kompass.gui.update_dialog import UpdateAllDialog
from cachy_kompass.gui.workers import TaskRunner
from cachy_kompass.installers import InstallerStatus, Rating
from cachy_kompass.models import KIND_INFO, SOURCE_INFO, DesktopEntry, Kind, MenuStatus, Program, Source, UpdateStatus
from cachy_kompass.sources import pacman

# Spalten im Reiter „Startmenü-Einträge“
ENTRY_COL_KIND, ENTRY_COL_COMMAND = 3, 4

RATING_COLOR = {Rating.BASE: GREY, Rating.RECOMMENDED: GREEN, Rating.OPTIONAL: ORANGE, Rating.DISCOURAGED: RED}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.setWindowIcon(QIcon.fromTheme("system-software-install", QIcon.fromTheme("applications-system")))
        self.resize(1300, 780)

        self.runner = TaskRunner()
        self.result: scanner.ScanResult | None = None
        #: Ergebnisse von „pacman -Rsp“ (Was ginge beim Deinstallieren mit weg?)
        self._removal_cache: dict[str, tuple[list[str], str]] = {}
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

        self.upgrade_action = QAction(QIcon.fromTheme("system-upgrade", QIcon.fromTheme("go-up")), "Alles aktualisieren …", self)
        self.upgrade_action.setToolTip("Systemupdate, Flatpaks usw. sichtbar in einem Terminalfenster installieren")
        self.upgrade_action.triggered.connect(self.update_everything)
        bar.addAction(self.upgrade_action)

        self.backup_action = QAction(QIcon.fromTheme("document-save"), "Liste sichern …", self)
        self.backup_action.setToolTip(
            "Speichert alle installierten Programme als Skript – damit lässt sich nach einer "
            "Neuinstallation alles wieder einspielen"
        )
        self.backup_action.triggered.connect(self.save_backup)
        bar.addAction(self.backup_action)
        bar.addSeparator()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Suchen (in allen Reitern) …")
        self.search.setToolTip("Durchsucht Namen, Beschreibungen, Startmenü-Einträge, Befehle und Pfade")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(200)
        self.search.setMaximumWidth(260)
        self.search.textChanged.connect(self._apply_search)
        bar.addWidget(self.search)

        # Zweite Zeile: alle Filter (eine Zeile allein ist auf normalen Bildschirmen zu schmal)
        self.addToolBarBreak()
        bar = QToolBar("Filter")
        bar.setMovable(False)
        self.addToolBar(bar)
        bar.addWidget(QLabel(" Filter: "))

        self.source_filter = QComboBox()
        self.source_filter.addItem("Alle Quellen", None)
        for src, info in SOURCE_INFO.items():
            self.source_filter.addItem(info.label, src)
        self.source_filter.currentIndexChanged.connect(
            lambda: self.proxy.update_filter(source=self.source_filter.currentData())
        )
        bar.addWidget(self.source_filter)

        # Filter „Art“: Ausklappliste mit Häkchen – frei kombinierbar, gilt für Programme und Startmenü-Einträge
        self.kind_button = QToolButton()
        self.kind_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.kind_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.kind_button.setToolTip("Welche Arten von Programmen angezeigt werden – mehrere gleichzeitig möglich")
        kind_menu = QMenu(self.kind_button)
        self.kind_boxes: dict[Kind, QCheckBox] = {}
        for kind, label in KIND_CHECKBOX_TEXT.items():
            # Häkchen als Widget im Menü: so bleibt das Menü beim Anklicken offen
            box = QCheckBox(label)
            box.setChecked(kind in DEFAULT_KINDS)
            box.setToolTip(KIND_INFO[kind])
            box.setContentsMargins(8, 2, 8, 2)
            box.toggled.connect(self._kinds_changed)
            action = QWidgetAction(kind_menu)
            action.setDefaultWidget(box)
            kind_menu.addAction(action)
            self.kind_boxes[kind] = box
        self.kind_button.setMenu(kind_menu)
        self._update_kind_button()
        bar.addWidget(self.kind_button)
        bar.addSeparator()

        self.menu_filter = QComboBox()
        self.menu_filter.addItem("Startmenü: egal", None)
        self.menu_filter.addItem("Startmenü: vorhanden", MenuStatus.VISIBLE)
        self.menu_filter.addItem("Startmenü: versteckt", MenuStatus.HIDDEN)
        self.menu_filter.addItem("Startmenü: fehlt", MenuStatus.NONE)
        self.menu_filter.currentIndexChanged.connect(
            lambda: self.proxy.update_filter(menu=self.menu_filter.currentData())
        )
        bar.addWidget(self.menu_filter)

        self.date_filter = QComboBox()
        self.date_filter.setToolTip("Nur kürzlich installierte Programme zeigen")
        for label, days in [("Installiert: egal", None), ("Installiert: letzte 7 Tage", 7),
                            ("Installiert: letzte 30 Tage", 30), ("Installiert: letztes Jahr", 365)]:
            self.date_filter.addItem(label, days)
        self.date_filter.currentIndexChanged.connect(
            lambda: self.proxy.update_filter(installed_within_days=self.date_filter.currentData())
        )
        bar.addWidget(self.date_filter)

        # Seltener gebrauchte Filter als Häkchen in einer Ausklappliste
        self.more_button = QToolButton()
        self.more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.more_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        more_menu = QMenu(self.more_button)

        def add_box(text: str, tooltip: str, handler) -> QCheckBox:
            box = QCheckBox(text)
            box.setToolTip(tooltip)
            box.setContentsMargins(8, 2, 8, 2)
            box.toggled.connect(handler)
            box.toggled.connect(self._update_more_button)
            action = QWidgetAction(more_menu)
            action.setDefaultWidget(box)
            more_menu.addAction(action)
            return box

        self.outdated_box = add_box(
            "Nur veraltete", "Nur Programme mit neuerer Version (erst nach „Nach Updates suchen“)",
            lambda on: self.proxy.update_filter(only_outdated=on),
        )
        self.manual_box = add_box(
            "Nur ohne Auto-Update", "Programme, die beim normalen Systemupdate nicht (sicher) mitaktualisiert werden",
            lambda on: self.proxy.update_filter(only_manual_update=on),
        )
        self.duplicates_box = add_box(
            "Nur doppelt installierte", "Programme, die aus mehreren Quellen installiert sind (z. B. Repo und Flatpak)",
            lambda on: self.proxy.update_filter(only_duplicates=on),
        )
        self.deps_box = add_box(
            "Abhängigkeiten zeigen", "Auch Bibliotheken und automatisch mitinstallierte Pakete anzeigen",
            self._toggle_dependencies,
        )
        self.more_boxes = [self.outdated_box, self.manual_box, self.duplicates_box, self.deps_box]
        self.more_button.setMenu(more_menu)
        self._update_more_button()
        bar.addWidget(self.more_button)

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

        self.reboot_banner = QLabel()
        self.reboot_banner.setWordWrap(True)
        self.reboot_banner.setStyleSheet(
            "background-color: rgba(217,138,0,0.18); border: 1px solid #d98a00; border-radius: 4px; padding: 6px"
        )
        self.reboot_banner.hide()
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.reboot_banner)
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

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
        for col, width in enumerate([180, 90, 110, 80, 85, 95, 105, 70, 90]):
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
        self.copy_launch_button = QPushButton(QIcon.fromTheme("utilities-terminal"), "Startbefehl kopieren")
        self.copy_launch_button.setToolTip("Befehl, mit dem das Programm im Terminal oder über Alt+F2 startet")
        self.copy_launch_button.clicked.connect(self.copy_launch)
        for b in (self.create_button, self.remove_button, self.copy_button, self.copy_launch_button):
            b.setEnabled(False)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.details)
        buttons = QHBoxLayout()
        buttons.addWidget(self.create_button)
        buttons.addWidget(self.remove_button)
        right_layout.addLayout(buttons)
        copy_buttons = QHBoxLayout()
        copy_buttons.addWidget(self.copy_launch_button)
        copy_buttons.addWidget(self.copy_button)
        right_layout.addLayout(copy_buttons)

        splitter = QSplitter()
        splitter.addWidget(self.table)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([980, 400])
        return splitter

    def _build_entries_tab(self) -> QWidget:
        info = QLabel(
            "Alle Startmenü-Einträge auf diesem System. Unter „Startbefehl“ steht, wie du das Programm "
            "auch im Terminal oder über Alt+F2 startest. „Programm fehlt“ bedeutet: Der Eintrag "
            "zeigt auf ein Programm, das es nicht (mehr) gibt – er ist also vermutlich kaputt."
        )
        info.setWordWrap(True)
        self.entries_table = QTableWidget(0, 6)
        self.entries_table.setHorizontalHeaderLabels(["Name", "Sichtbar", "Gehört zu", "Art", "Startbefehl", "Datei"])
        self.entries_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.entries_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.entries_table.setSortingEnabled(True)
        self.entries_table.verticalHeader().setVisible(False)
        self.entries_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        for col, width in enumerate([220, 90, 240, 110, 200]):
            self.entries_table.setColumnWidth(col, width)
        self.entries_table.itemSelectionChanged.connect(self._entry_selected)

        self.entry_edit_button = QPushButton(QIcon.fromTheme("document-edit"), "Bearbeiten …")
        self.entry_edit_button.setToolTip(
            "Name, Symbol, Startbefehl usw. ändern. Systemeinträge bleiben unverändert – "
            "die Änderung wird als eigene Fassung in deinem Benutzerordner gespeichert."
        )
        self.entry_edit_button.clicked.connect(self._edit_selected_entry)
        self.entry_visible_button = QPushButton(QIcon.fromTheme("view-visible"), "Einblenden")
        self.entry_visible_button.setToolTip("Den Eintrag im Startmenü zeigen bzw. verstecken")
        self.entry_visible_button.clicked.connect(self._toggle_selected_entry)
        self.entry_remove_button = QPushButton(QIcon.fromTheme("list-remove"), "Entfernen …")
        self.entry_remove_button.setToolTip(
            "Nur Einträge in deinem Benutzerordner können entfernt werden, Systemeinträge nicht."
        )
        self.entry_remove_button.clicked.connect(self._remove_selected_entry)
        self.entry_copy_button = QPushButton(QIcon.fromTheme("utilities-terminal"), "Startbefehl kopieren")
        self.entry_copy_button.setToolTip("Befehl, mit dem das Programm im Terminal oder über Alt+F2 startet")
        self.entry_copy_button.clicked.connect(self._copy_entry_command)
        for b in (self.entry_edit_button, self.entry_visible_button, self.entry_remove_button, self.entry_copy_button):
            b.setEnabled(False)

        buttons = QHBoxLayout()
        buttons.addWidget(self.entry_copy_button)
        buttons.addStretch(1)
        buttons.addWidget(self.entry_edit_button)
        buttons.addWidget(self.entry_visible_button)
        buttons.addWidget(self.entry_remove_button)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(info)
        layout.addWidget(self.entries_table)
        layout.addLayout(buttons)
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
        self.upgrade_action.setEnabled(not busy and self.result is not None)
        self.backup_action.setEnabled(not busy and self.result is not None)
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
        self._removal_cache.clear()
        self._show_reboot_hint()
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
        kinds = self.selected_kinds()
        for table in (self.entries_table, self.installer_table):
            for row in range(table.rowCount()):
                cells = (table.item(row, col) for col in range(table.columnCount()))
                # Tooltips mit durchsuchen – dort steht z. B. der vollständige Startbefehl
                row_text = " ".join(f"{c.text()} {c.toolTip()}" for c in cells if c is not None).lower()
                visible = all(w in row_text for w in words)
                if table is self.entries_table:
                    kind_item = table.item(row, ENTRY_COL_KIND)
                    visible = visible and (kind_item is None or kind_item.data(Qt.ItemDataRole.UserRole) in kinds)
                table.setRowHidden(row, not visible)

    def selected_kinds(self) -> frozenset[Kind]:
        return frozenset(kind for kind, box in self.kind_boxes.items() if box.isChecked())

    def _update_kind_button(self) -> None:
        kinds = self.selected_kinds()
        if not kinds:
            text = "Art: keine"
        elif len(kinds) == len(self.kind_boxes):
            text = "Art: alle"
        else:
            text = "Art: " + ", ".join(KIND_CHECKBOX_TEXT[k] for k in self.kind_boxes if k in kinds)
        self.kind_button.setText(text)

    def _kinds_changed(self, _checked: bool = False) -> None:
        self._update_kind_button()
        self.proxy.update_filter(kinds=self.selected_kinds())
        self._apply_search()

    def _update_more_button(self, _checked: bool = False) -> None:
        active = [b.text() for b in self.more_boxes if b.isChecked()]
        self.more_button.setText(f"Weitere Filter ({len(active)})" if active else "Weitere Filter")
        self.more_button.setToolTip("Aktiv: " + ", ".join(active) if active else "Weitere Filter")

    def _toggle_dependencies(self, on: bool) -> None:
        self.proxy.update_filter(show_dependencies=on)

    # --- Detailansicht -------------------------------------------------------

    def current_program(self) -> Program | None:
        index = self.table.currentIndex()
        return index.data(PROGRAM_ROLE) if index.isValid() else None

    def _show_details(self, index: QModelIndex, _previous: QModelIndex | None = None) -> None:
        program = index.data(PROGRAM_ROLE) if index.isValid() else None
        if program is None:
            for b in (self.create_button, self.remove_button, self.copy_button, self.copy_launch_button):
                b.setEnabled(False)
            return
        removal = self._removal_preview(program)
        sizes = {p.name: p.size_bytes for p in self.result.programs} if removal and self.result else None
        self.details.setHtml(details.program_html(program, removal, sizes))
        self.create_button.setEnabled(True)
        self.remove_button.setEnabled(any(desktop.can_remove(e) for e in program.desktop_entries))
        self.copy_button.setEnabled(True)
        self.copy_launch_button.setEnabled(bool(desktop.launch_command(program)))

    def _removal_preview(self, program: Program) -> tuple[list[str], str] | None:
        """Trockenlauf von pacman: Was würde beim Deinstallieren mit entfernt? (zwischengespeichert)"""
        if program.source not in (Source.REPO, Source.AUR) or not shutil.which("pacman"):
            return None
        if program.name not in self._removal_cache:
            self._removal_cache[program.name] = pacman.removal_preview(program.name)
        return self._removal_cache[program.name]

    def _show_reboot_hint(self) -> None:
        assert self.result is not None
        info = self.result.reboot
        if info.needed:
            self.reboot_banner.setText(
                f"<b>🔄 Neustart empfohlen.</b> {info.message()} Erst nach einem Neustart läuft "
                "alles mit den neuen Versionen."
            )
        self.reboot_banner.setVisible(info.needed)

    # --- Alles aktualisieren / Liste sichern -----------------------------------

    def update_everything(self) -> None:
        if not self.result:
            return
        dialog = UpdateAllDialog(self.result.programs, self)
        if not dialog.exec():
            return
        commands = dialog.selected_commands()
        if terminal.run_in_terminal(commands):
            self._status("Terminal geöffnet. Wenn die Updates fertig sind, auf „Neu einlesen“ klicken.")
        else:
            QGuiApplication.clipboard().setText(terminal.describe(commands))
            QMessageBox.information(
                self,
                "Kein Terminal gefunden",
                "Es wurde kein Terminalprogramm gefunden. Die Befehle wurden in die Zwischenablage kopiert:\n\n"
                f"{terminal.describe(commands)}",
            )

    def save_backup(self) -> None:
        if not self.result:
            return
        start = Path.home() / backup.default_filename()
        path, _ = QFileDialog.getSaveFileName(
            self, "Programmliste sichern", str(start), "Shell-Skript (*.sh);;Alle Dateien (*)"
        )
        if not path:
            return
        try:
            Path(path).write_text(backup.build_script(self.result.programs, hostname=socket.gethostname()), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Fehler", f"Die Datei konnte nicht gespeichert werden:\n{exc}")
            return
        QMessageBox.information(
            self,
            "Programmliste gesichert",
            f"Gespeichert in:\n{path}\n\nDie Datei ist gleichzeitig eine lesbare Liste und ein Skript. "
            "Kopiere sie am besten auf einen USB-Stick oder in die Cloud. Nach einer Neuinstallation "
            f"stellst du die Programme im Terminal wieder her mit:\n\n    bash {Path(path).name}\n\n"
            "Vor jeder Installation wird nachgefragt.",
        )

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
        elif program.menu_status is MenuStatus.HIDDEN and self._offer_unhide(program):
            return
        dialog = EntryDialog(program, self)
        if dialog.exec() and dialog.created_path:
            self._status(f"Eintrag angelegt: {dialog.created_path}")
            self._rematch()

    def _offer_unhide(self, program: Program) -> bool:
        """Versteckten Eintrag einblenden statt einen neuen anzulegen? ``True`` = erledigt bzw. abgebrochen."""
        entry = program.desktop_entries[0]
        box = QMessageBox(
            QMessageBox.Icon.Question,
            "Versteckter Eintrag vorhanden",
            f"„{program.display_name}“ hat schon einen Startmenü-Eintrag („{entry.name}“), er ist aber "
            "ausgeblendet. Oft ist das Absicht (z. B. bei Hilfsprogrammen).\n\n"
            "Soll der vorhandene Eintrag eingeblendet werden, oder möchtest du einen neuen anlegen?",
            parent=self,
        )
        unhide = box.addButton("Einblenden", QMessageBox.ButtonRole.AcceptRole)
        new = box.addButton("Neuen anlegen …", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Abbrechen", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is new:
            return False
        if box.clickedButton() is unhide:
            try:
                desktop.set_visible(entry, True)
            except OSError as exc:
                QMessageBox.critical(self, "Fehler", str(exc))
                return True
            self._status(f"„{entry.name}“ eingeblendet.")
            self._rematch()
        return True

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
        system = desktop.overridden_system_entry(entry)
        if system:
            text = (
                f"Deine eigene Fassung von „{entry.name}“ entfernen und das Original wiederherstellen?\n\n"
                f"Entfernt wird: {entry.path}\nDanach gilt wieder: {system}"
            )
        else:
            text = f"Den Eintrag „{entry.name}“ wirklich entfernen?\n\n{entry.path}"
        if not system and not entry.created_by_us:
            text += (
                "\n\nAchtung: Diesen Eintrag hat nicht der Software-Kompass angelegt, sondern du selbst "
                "oder ein anderes Programm (z. B. Steam, Gear Lever, AppImageLauncher). "
                "Das Programm selbst bleibt installiert – nur der Menüeintrag verschwindet."
            )
        box = QMessageBox(QMessageBox.Icon.Question, "Eintrag entfernen", text, parent=self)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText("Wiederherstellen" if system else "Entfernen")
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

    def copy_launch(self) -> None:
        program = self.current_program()
        command = desktop.launch_command(program) if program else ""
        if command:
            QGuiApplication.clipboard().setText(command)
            self._status(f"In die Zwischenablage kopiert: {command}")

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
            kind = desktop.entry_kind(e, owner)
            cells = [
                (e.name, None),
                ("ja" if e.visible else "nein (von dir)" if e.hidden_by_user else "nein",
                 GREEN if e.visible else ORANGE if e.hidden_by_user else GREY),
                (owner_text, None),
                (KIND_TEXT[kind], None),
                (desktop.shell_command(e.exec) if exists else f"✘ Programm fehlt: {missing}", None if exists else RED),
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
                if col == ENTRY_COL_KIND:
                    item.setData(Qt.ItemDataRole.UserRole, kind)
                    item.setToolTip(KIND_INFO[kind])
                if col == ENTRY_COL_COMMAND:
                    if missing:
                        item.setToolTip(f"Nicht gefunden: {missing}\nStartbefehl im Eintrag: {e.exec}")
                    else:
                        item.setToolTip(
                            f"Im Terminal oder über Alt+F2 starten mit: {desktop.shell_command(e.exec)}\n"
                            f"Startbefehl im Eintrag: {e.exec}"
                        )
                table.setItem(row, col, item)
        table.setSortingEnabled(True)
        self._apply_search()
        self._entry_selected()  # Knöpfe passend zum (neu eingelesenen) ausgewählten Eintrag

    def _selected_entry(self) -> DesktopEntry | None:
        rows = self.entries_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.entries_table.item(rows[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _entry_selected(self) -> None:
        entry = self._selected_entry()
        self.entry_edit_button.setEnabled(entry is not None)
        self.entry_visible_button.setEnabled(entry is not None)
        self.entry_remove_button.setEnabled(bool(entry and desktop.can_remove(entry)))
        self.entry_copy_button.setEnabled(bool(entry and desktop.shell_command(entry.exec)))
        if entry is None:
            return
        self.entry_visible_button.setText("Ausblenden" if entry.visible else "Einblenden")
        self.entry_visible_button.setIcon(QIcon.fromTheme("view-hidden" if entry.visible else "view-visible"))
        restores = desktop.can_remove(entry) and desktop.overridden_system_entry(entry) is not None
        self.entry_remove_button.setText("Original wiederherstellen …" if restores else "Entfernen …")

    def _edit_selected_entry(self) -> None:
        entry = self._selected_entry()
        if entry is None or self.result is None:
            return
        dialog = EntryDialog(self.result.owner_of(entry), self, entry=entry)
        if dialog.exec() and dialog.created_path:
            self._status(f"Eintrag gespeichert: {dialog.created_path}")
            self._rematch()

    def _toggle_selected_entry(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        try:
            path = desktop.set_visible(entry, not entry.visible)
        except OSError as exc:
            QMessageBox.critical(self, "Fehler", str(exc))
            return
        word = "ausgeblendet" if entry.visible else "eingeblendet"
        self._status(f"„{entry.name}“ {word} (gespeichert in {path}).")
        command = desktop.shell_command(entry.exec)
        if entry.visible and command:
            QMessageBox.information(
                self,
                "Eintrag ausgeblendet",
                f"„{entry.name}“ erscheint nicht mehr im Startmenü. Das Programm ist aber weiter "
                f"installiert und lässt sich so starten:\n\n"
                f"    {command}\n\n"
                "– im Terminal (z. B. Konsole) oder nach Alt+F2 (KRunner) eingeben.\n\n"
                "Wieder einblenden: hier im Reiter „Startmenü-Einträge“ den Eintrag wählen und "
                "„Einblenden“ bzw. „Original wiederherstellen …“ klicken.",
            )
        self._rematch()

    def _copy_entry_command(self) -> None:
        entry = self._selected_entry()
        command = desktop.shell_command(entry.exec) if entry else ""
        if command:
            QGuiApplication.clipboard().setText(command)
            self._status(f"In die Zwischenablage kopiert: {command}")

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

