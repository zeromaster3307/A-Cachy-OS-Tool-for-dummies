"""Tabellenmodell und Filter für die Programmliste."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor

from cachy_kompass import util
from cachy_kompass.models import KIND_INFO, AutoUpdate, Kind, MenuStatus, Program, Source, UpdateStatus

GREEN = QColor("#2e9d4f")
ORANGE = QColor("#d98a00")
RED = QColor("#d64545")
GREY = QColor("#8a8a8a")

COLUMNS = [
    "Programm", "Version", "Quelle", "Art", "Startmenü", "Auto-Update", "Aktuell?", "Größe", "Installiert", "Beschreibung",
]
(
    COL_NAME, COL_VERSION, COL_SOURCE, COL_KIND, COL_MENU, COL_AUTO, COL_UPDATE, COL_SIZE, COL_DATE, COL_DESC,
) = range(len(COLUMNS))

KIND_TEXT = {Kind.APP: "🪟 App", Kind.COMMAND: "⌨ Befehl", Kind.OTHER: "📦 Sonstiges"}

#: Beschriftung der Häkchen im Filter „Art“
KIND_CHECKBOX_TEXT = {Kind.APP: "🪟 Apps", Kind.COMMAND: "⌨ Befehle", Kind.OTHER: "📦 Sonstiges"}
#: Standard: nur Programme mit Fenster
DEFAULT_KINDS = frozenset({Kind.APP})

MENU_TEXT = {MenuStatus.VISIBLE: "✔ ja", MenuStatus.HIDDEN: "◐ versteckt", MenuStatus.NONE: "✘ nein"}
MENU_COLOR = {MenuStatus.VISIBLE: GREEN, MenuStatus.HIDDEN: ORANGE, MenuStatus.NONE: GREY}
AUTO_TEXT = {AutoUpdate.YES: "✔ ja", AutoUpdate.PARTIAL: "◐ teilweise", AutoUpdate.NO: "✘ nein"}
AUTO_COLOR = {AutoUpdate.YES: GREEN, AutoUpdate.PARTIAL: ORANGE, AutoUpdate.NO: RED}
UPDATE_COLOR = {
    UpdateStatus.CURRENT: GREEN,
    UpdateStatus.OUTDATED: RED,
    UpdateStatus.UNKNOWN: ORANGE,
    UpdateStatus.NOT_CHECKABLE: GREY,
    UpdateStatus.NOT_CHECKED: GREY,
}

SORT_ROLE = Qt.ItemDataRole.UserRole + 1
PROGRAM_ROLE = Qt.ItemDataRole.UserRole + 2


def date_text(p: Program) -> str:
    if p.installed_at is None:
        return ""
    return ("ca. " if p.installed_approx else "") + p.installed_at.strftime("%d.%m.%Y")


def date_tooltip(p: Program) -> str:
    if p.installed_at is None:
        return "Installationsdatum unbekannt"
    when = p.installed_at.strftime("%d.%m.%Y um %H:%M")
    if p.installed_approx:
        return f"Ungefähr: {when} – Änderungsdatum der Programmdateien (bei Updates evtl. später)"
    return f"Installiert am {when} (laut pacman-Protokoll)"


def update_text(p: Program) -> str:
    u = p.update
    if u.status is UpdateStatus.OUTDATED:
        return f"⬆ {u.latest}" if u.latest else "⬆ Update verfügbar"
    if u.status is UpdateStatus.CURRENT:
        return "✔ aktuell"
    return u.status.value


class ProgramTableModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self.programs: list[Program] = []

    def set_programs(self, programs: list[Program]) -> None:
        self.beginResetModel()
        self.programs = programs
        self.endResetModel()

    def refresh(self) -> None:
        """Nach Update-Prüfung oder neuem Startmenü-Eintrag alles neu zeichnen."""
        if self.programs:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.programs) - 1, len(COLUMNS) - 1))

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self.programs)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        p = self.programs[index.row()]
        col = index.column()
        if role == PROGRAM_ROLE:
            return p
        if role == Qt.ItemDataRole.DisplayRole:
            return [
                f"{p.display_name}  ({len(p.duplicates) + 1}×)" if p.duplicates else p.display_name,
                p.version,
                p.info.label,
                KIND_TEXT[p.kind],
                MENU_TEXT[p.menu_status],
                AUTO_TEXT[p.info.auto_update],
                update_text(p),
                util.format_size(p.size_bytes) if p.size_bytes else "",
                date_text(p),
                p.description,
            ][col]
        if role == SORT_ROLE:
            if col == COL_NAME:
                return p.display_name.lower()
            if col == COL_KIND:
                return list(Kind).index(p.kind)
            if col == COL_MENU:
                return list(MenuStatus).index(p.menu_status)
            if col == COL_AUTO:
                return list(AutoUpdate).index(p.info.auto_update)
            if col == COL_SIZE:
                return p.size_bytes
            if col == COL_DATE:
                return p.installed_at.timestamp() if p.installed_at else 0.0
            if col == COL_UPDATE:
                return [UpdateStatus.OUTDATED, UpdateStatus.UNKNOWN, UpdateStatus.CURRENT,
                        UpdateStatus.NOT_CHECKABLE, UpdateStatus.NOT_CHECKED].index(p.update.status)
            return str(self.data(index)).lower()
        if role == Qt.ItemDataRole.TextAlignmentRole and col == COL_SIZE:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ForegroundRole:
            if col == COL_DATE and p.installed_approx:
                return GREY
            if col == COL_MENU:
                return MENU_COLOR[p.menu_status]
            if col == COL_AUTO:
                return AUTO_COLOR[p.info.auto_update]
            if col == COL_UPDATE:
                return UPDATE_COLOR[p.update.status]
        if role == Qt.ItemDataRole.ToolTipRole:
            if col == COL_AUTO:
                return p.update_hint()
            if col == COL_UPDATE and p.update.note:
                return p.update.note
            if col == COL_SOURCE:
                return p.origin
            if col == COL_KIND:
                return KIND_INFO[p.kind]
            if col == COL_DATE:
                return date_tooltip(p)
            if col == COL_SIZE and p.source is Source.FLATPAK:
                return "Nur die App selbst – gemeinsam genutzte Laufzeiten kommen hinzu."
            if col == COL_NAME and p.duplicates:
                return "Auch installiert als: " + ", ".join(f"{d.display_name} ({d.info.label})" for d in p.duplicates)
            if col == COL_DESC:
                return p.description
        return None


class ProgramFilterModel(QSortFilterProxyModel):
    """Filtert nach Suchtext, Quelle, Startmenü-Status, Update-Status und Abhängigkeiten."""

    def __init__(self) -> None:
        super().__init__()
        self.search = ""
        self.source: Source | None = None
        self.menu: MenuStatus | None = None
        self.only_outdated = False
        self.only_manual_update = False
        self.show_dependencies = False
        self.kinds: frozenset[Kind] = DEFAULT_KINDS
        #: Nur Programme, die in den letzten N Tagen installiert wurden (None = egal)
        self.installed_within_days: int | None = None
        self.only_duplicates = False
        self.setSortRole(SORT_ROLE)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def update_filter(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.invalidateFilter()

    def filterAcceptsRow(self, row: int, parent: QModelIndex) -> bool:
        model: ProgramTableModel = self.sourceModel()  # type: ignore[assignment]
        p = model.programs[row]
        if not self.show_dependencies and not p.explicit:
            return False
        if self.source is not None and p.source is not self.source:
            return False
        if p.kind not in self.kinds:
            return False
        if self.menu is not None and p.menu_status is not self.menu:
            return False
        if self.only_outdated and p.update.status is not UpdateStatus.OUTDATED:
            return False
        if self.only_manual_update and p.info.auto_update is AutoUpdate.YES:
            return False
        if self.only_duplicates and not p.duplicates:
            return False
        if self.installed_within_days is not None:
            if p.installed_at is None:
                return False
            limit = datetime.now(p.installed_at.tzinfo) - timedelta(days=self.installed_within_days)
            if p.installed_at < limit:
                return False
        if self.search:
            haystack = p.search_text()
            return all(word in haystack for word in self.search.lower().split())
        return True
