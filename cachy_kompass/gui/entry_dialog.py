"""Dialog zum Anlegen eines eigenen Startmenü-Eintrags – oder zum Bearbeiten eines vorhandenen."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cachy_kompass import desktop
from cachy_kompass.i18n import _
from cachy_kompass.models import DesktopEntry, Program


class EntryDialog(QDialog):
    """Neuen Eintrag für ``program`` anlegen – oder, mit ``entry``, einen vorhandenen bearbeiten."""

    def __init__(
        self,
        program: Program | None,
        parent: QWidget | None = None,
        entry: DesktopEntry | None = None,
    ) -> None:
        super().__init__(parent)
        self.program = program
        self.entry = entry
        self.created_path: Path | None = None
        self.setMinimumWidth(560)

        if entry is not None:
            self.setWindowTitle(_("Startmenü-Eintrag „{name}“ bearbeiten").format(name=entry.name))
            if desktop.is_user_entry(entry):
                text = _("Der Eintrag liegt in deinem Benutzerordner und wird direkt geändert.")
            else:
                text = _(
                    "Dies ist ein Eintrag des Systems. Er selbst bleibt unverändert – deine Änderungen "
                    "werden als eigene Fassung in deinem Benutzerordner gespeichert, die ihn im "
                    "Startmenü ersetzt. Mit „Entfernen“ bzw. „Original wiederherstellen“ kommst du "
                    "jederzeit zum Original zurück. Hinweis: Ändert ein Update später den "
                    "Systemeintrag, gilt trotzdem weiter deine Fassung."
                )
            name, comment, exec_line, icon = entry.name, entry.comment, entry.exec, entry.icon
            terminal_default = entry.terminal
        else:
            assert program is not None
            self.setWindowTitle(_("Startmenü-Eintrag für „{name}“").format(name=program.display_name))
            text = _(
                "Hier legst du einen Eintrag an, über den du das Programm im Startmenü findest. "
                "Der Eintrag wird nur für deinen Benutzer gespeichert und kann jederzeit wieder "
                "entfernt werden."
            )
            name, comment = program.display_name, program.description
            exec_line, icon = desktop.suggest_exec(program), desktop.suggest_icon(program)
            terminal_default = program.info.cli_by_default
        intro = QLabel(text)
        intro.setWordWrap(True)

        self.name_edit = QLineEdit(name)
        self.comment_edit = QLineEdit(comment)
        self.comment_edit.setPlaceholderText(_("Optional: kurze Beschreibung"))

        self.exec_edit = QLineEdit(exec_line)
        self.exec_edit.setToolTip(_("Der Befehl, der beim Klick auf den Eintrag ausgeführt wird."))
        exec_browse = QPushButton(_("Durchsuchen …"))
        exec_browse.clicked.connect(self._browse_exec)
        exec_row = self._row(self.exec_edit, exec_browse)

        self.icon_edit = QLineEdit(icon)
        self.icon_edit.setToolTip(_("Name eines Symbols aus dem Symbol-Design oder Pfad zu einer Bilddatei."))
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(48, 48)
        icon_browse = QPushButton(_("Bild wählen …"))
        icon_browse.setToolTip(_("Eigenes Bild als Symbol verwenden (am besten SVG oder PNG)"))
        icon_browse.clicked.connect(self._browse_icon)
        self.icon_edit.textChanged.connect(self._update_icon_preview)
        icon_row = self._row(self.icon_preview, self.icon_edit, icon_browse)
        self.icon_hint = QLabel()
        self.icon_hint.setWordWrap(True)

        self.category = QComboBox()
        if entry is not None:
            self.category.addItem(_("(unverändert lassen)"), None)
        for key, label in desktop.CATEGORIES.items():
            self.category.addItem(label, key)

        self.terminal = QCheckBox(_("In einem Terminalfenster starten"))
        self.terminal.setChecked(terminal_default)
        terminal_hint = QLabel(
            _("Häkchen setzen bei Kommandozeilenprogrammen, also Programmen ohne eigenes Fenster.")
        )
        terminal_hint.setWordWrap(True)
        terminal_hint.setStyleSheet("color: gray")

        form = QFormLayout()
        form.addRow(_("Name im Menü:"), self.name_edit)
        form.addRow(_("Beschreibung:"), self.comment_edit)
        form.addRow(_("Startbefehl:"), exec_row)
        form.addRow(_("Symbol:"), icon_row)
        form.addRow("", self.icon_hint)
        form.addRow(_("Kategorie:"), self.category)
        form.addRow("", self.terminal)
        form.addRow("", terminal_hint)

        where = desktop.user_copy_path(entry) if entry is not None else desktop.user_applications_dir()
        target = QLabel(_("Wird gespeichert in: {path}").format(path=where))
        target.setStyleSheet("color: gray")
        target.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(_("Speichern") if entry is not None else _("Eintrag anlegen"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(_("Abbrechen"))
        buttons.accepted.connect(self._create)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addLayout(form)
        layout.addWidget(target)
        layout.addWidget(buttons)
        self._update_icon_preview()

    @staticmethod
    def _row(*widgets: QWidget) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        for w in widgets:
            row.addWidget(w)
        return container

    def _browse_exec(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(self, _("Programmdatei auswählen"), str(Path.home()))
        if path:
            self.exec_edit.setText(desktop.quote_exec_arg(path))

    def _browse_icon(self) -> None:
        start = str(Path.home() / "Downloads") if (Path.home() / "Downloads").is_dir() else str(Path.home())
        path, _filter = QFileDialog.getOpenFileName(
            self,
            _("Bild für das Symbol auswählen"),
            start,
            _("Bilder") + " (*.svg *.png *.xpm *.jpg *.jpeg *.ico *.webp *.bmp *.gif);;" + _("Alle Dateien") + " (*)",
        )
        if path:
            self.icon_edit.setText(path)

    def _icon_found(self, value: str) -> bool:
        if not value:
            return False
        if value.startswith("/"):
            return not QIcon(value).isNull() and Path(value).is_file()
        return QIcon.hasThemeIcon(value)

    def _update_icon_preview(self) -> None:
        value = self.icon_edit.text().strip()
        found = self._icon_found(value)
        icon = (QIcon(value) if value.startswith("/") else QIcon.fromTheme(value)) if found else QIcon()
        if icon.isNull():
            icon = QIcon.fromTheme("application-x-executable")
        self.icon_preview.setPixmap(icon.pixmap(48, 48))
        if found and value.startswith("/"):
            self.icon_hint.setText(_("✔ Eigenes Bild – es wird beim Anlegen in deinen Symbolordner kopiert."))
            self.icon_hint.setStyleSheet("color: #2e9d4f")
        elif found:
            self.icon_hint.setText(_("✔ Passendes Symbol im Symbol-Design gefunden."))
            self.icon_hint.setStyleSheet("color: #2e9d4f")
        else:
            self.icon_hint.setText(_(
                "⚠ Kein Symbol mit diesem Namen gefunden. Klicke auf „Bild wählen …“ und "
                "nimm z. B. das Logo von der Webseite des Programms (am besten SVG oder PNG)."
            ))
            self.icon_hint.setStyleSheet("color: #d98a00")

    def _prepare_icon(self) -> str:
        """Wandelt Bilder, die das Startmenü nicht direkt versteht (JPG, ICO …), in PNG um."""
        value = self.icon_edit.text().strip()
        if not value.startswith("/") or Path(value).suffix.lower() in desktop.ICON_FORMATS:
            return value
        image = QImage(value)
        if image.isNull():
            raise ValueError(_("Das Bild „{path}“ konnte nicht gelesen werden.").format(path=value))
        if max(image.width(), image.height()) > 256:
            image = image.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        converted = Path(tempfile.mkdtemp(prefix="cachy-kompass-")) / (Path(value).stem + ".png")
        if not image.save(str(converted), "PNG"):
            raise ValueError(_("Das Bild konnte nicht in PNG umgewandelt werden."))
        return str(converted)

    def _create(self) -> None:
        name = self.name_edit.text().strip()
        exec_line = self.exec_edit.text().strip()
        if not name or not exec_line:
            QMessageBox.warning(self, _("Angaben fehlen"), _("Bitte einen Namen und einen Startbefehl eintragen."))
            return
        # Beim Bearbeiten nur prüfen, wenn der Startbefehl geändert wurde
        unchanged = self.entry is not None and exec_line == self.entry.exec
        target = "" if unchanged else desktop.missing_program(exec_line)
        if target:
            answer = QMessageBox.question(
                self,
                _("Programm nicht gefunden"),
                _(
                    "Das Programm „{program}“ wurde nicht gefunden. Der Eintrag würde "
                    "vermutlich nicht funktionieren.\n\nTrotzdem speichern?"
                ).format(program=target),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            if self.entry is not None:
                self.created_path = desktop.edit_entry(self.entry, self._changes(name, exec_line))
            else:
                self.created_path = self._create_new(name, exec_line)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, _("Fehler"), _("Der Eintrag konnte nicht gespeichert werden:") + f"\n{exc}")
            return
        problems = desktop.validate(self.created_path)
        if problems:
            QMessageBox.information(self, _("Hinweis"), _("Der Eintrag wurde gespeichert, die Prüfung meldet aber:") + f"\n\n{problems}")
        self.accept()

    def _changes(self, name: str, exec_line: str) -> dict[str, str | None]:
        """Nur, was wirklich geändert wurde – sonst gingen z. B. Übersetzungen des Namens verloren."""
        assert self.entry is not None
        e = self.entry
        changes: dict[str, str | None] = {}
        if name != e.name:
            changes["Name"] = name
        comment = self.comment_edit.text().strip()
        if comment != e.comment:
            changes["Comment"] = comment or None
        if exec_line != e.exec:
            changes["Exec"] = exec_line
        icon = self._prepare_icon()
        if icon != e.icon:
            changes["Icon"] = icon or None
        if self.category.currentData():
            changes["Categories"] = f"{self.category.currentData()};"
        if self.terminal.isChecked() != e.terminal:
            changes["Terminal"] = "true" if self.terminal.isChecked() else "false"
        return changes

    def _create_new(self, name: str, exec_line: str) -> Path:
        return desktop.create_entry(
            name=name,
            exec_line=exec_line,
            icon=self._prepare_icon(),
            comment=self.comment_edit.text().strip(),
            categories=[self.category.currentData()],
            terminal=self.terminal.isChecked(),
        )
