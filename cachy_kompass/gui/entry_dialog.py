"""Dialog zum Anlegen eines eigenen Startmenü-Eintrags."""

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
from cachy_kompass.models import Program


class EntryDialog(QDialog):
    def __init__(self, program: Program, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.program = program
        self.created_path: Path | None = None
        self.setWindowTitle(f"Startmenü-Eintrag für „{program.display_name}“")
        self.setMinimumWidth(560)

        intro = QLabel(
            "Hier legst du einen Eintrag an, über den du das Programm im Startmenü findest. "
            "Der Eintrag wird nur für deinen Benutzer gespeichert und kann jederzeit wieder "
            "entfernt werden."
        )
        intro.setWordWrap(True)

        self.name_edit = QLineEdit(program.display_name)
        self.comment_edit = QLineEdit(program.description)
        self.comment_edit.setPlaceholderText("Optional: kurze Beschreibung")

        self.exec_edit = QLineEdit(desktop.suggest_exec(program))
        self.exec_edit.setToolTip("Der Befehl, der beim Klick auf den Eintrag ausgeführt wird.")
        exec_browse = QPushButton("Durchsuchen …")
        exec_browse.clicked.connect(self._browse_exec)
        exec_row = self._row(self.exec_edit, exec_browse)

        self.icon_edit = QLineEdit(desktop.suggest_icon(program))
        self.icon_edit.setToolTip("Name eines Symbols aus dem Symbol-Design oder Pfad zu einer Bilddatei.")
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(48, 48)
        icon_browse = QPushButton("Bild wählen …")
        icon_browse.setToolTip("Eigenes Bild als Symbol verwenden (am besten SVG oder PNG)")
        icon_browse.clicked.connect(self._browse_icon)
        self.icon_edit.textChanged.connect(self._update_icon_preview)
        icon_row = self._row(self.icon_preview, self.icon_edit, icon_browse)
        self.icon_hint = QLabel()
        self.icon_hint.setWordWrap(True)

        self.category = QComboBox()
        for key, label in desktop.CATEGORIES.items():
            self.category.addItem(label, key)

        self.terminal = QCheckBox("In einem Terminalfenster starten")
        self.terminal.setChecked(program.info.cli_by_default)
        terminal_hint = QLabel(
            "Häkchen setzen bei Kommandozeilenprogrammen, also Programmen ohne eigenes Fenster."
        )
        terminal_hint.setWordWrap(True)
        terminal_hint.setStyleSheet("color: gray")

        form = QFormLayout()
        form.addRow("Name im Menü:", self.name_edit)
        form.addRow("Beschreibung:", self.comment_edit)
        form.addRow("Startbefehl:", exec_row)
        form.addRow("Symbol:", icon_row)
        form.addRow("", self.icon_hint)
        form.addRow("Kategorie:", self.category)
        form.addRow("", self.terminal)
        form.addRow("", terminal_hint)

        target = QLabel(f"Wird gespeichert in: {desktop.user_applications_dir()}")
        target.setStyleSheet("color: gray")
        target.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Eintrag anlegen")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
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
        path, _ = QFileDialog.getOpenFileName(self, "Programmdatei auswählen", str(Path.home()))
        if path:
            self.exec_edit.setText(desktop.quote_exec_arg(path))

    def _browse_icon(self) -> None:
        start = str(Path.home() / "Downloads") if (Path.home() / "Downloads").is_dir() else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Bild für das Symbol auswählen",
            start,
            "Bilder (*.svg *.png *.xpm *.jpg *.jpeg *.ico *.webp *.bmp *.gif);;Alle Dateien (*)",
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
            self.icon_hint.setText("✔ Eigenes Bild – es wird beim Anlegen in deinen Symbolordner kopiert.")
            self.icon_hint.setStyleSheet("color: #2e9d4f")
        elif found:
            self.icon_hint.setText("✔ Passendes Symbol im Symbol-Design gefunden.")
            self.icon_hint.setStyleSheet("color: #2e9d4f")
        else:
            self.icon_hint.setText(
                "⚠ Kein Symbol mit diesem Namen gefunden. Klicke auf „Bild wählen …“ und "
                "nimm z. B. das Logo von der Webseite des Programms (am besten SVG oder PNG)."
            )
            self.icon_hint.setStyleSheet("color: #d98a00")

    def _prepare_icon(self) -> str:
        """Wandelt Bilder, die das Startmenü nicht direkt versteht (JPG, ICO …), in PNG um."""
        value = self.icon_edit.text().strip()
        if not value.startswith("/") or Path(value).suffix.lower() in desktop.ICON_FORMATS:
            return value
        image = QImage(value)
        if image.isNull():
            raise ValueError(f"Das Bild „{value}“ konnte nicht gelesen werden.")
        if max(image.width(), image.height()) > 256:
            image = image.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        converted = Path(tempfile.mkdtemp(prefix="cachy-kompass-")) / (Path(value).stem + ".png")
        if not image.save(str(converted), "PNG"):
            raise ValueError("Das Bild konnte nicht in PNG umgewandelt werden.")
        return str(converted)

    def _create(self) -> None:
        name = self.name_edit.text().strip()
        exec_line = self.exec_edit.text().strip()
        if not name or not exec_line:
            QMessageBox.warning(self, "Angaben fehlen", "Bitte einen Namen und einen Startbefehl eintragen.")
            return
        target = desktop.missing_program(exec_line)
        if target:
            answer = QMessageBox.question(
                self,
                "Programm nicht gefunden",
                f"Das Programm „{target}“ wurde nicht gefunden. Der Eintrag würde "
                "vermutlich nicht funktionieren.\n\nTrotzdem anlegen?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            self.created_path = desktop.create_entry(
                name=name,
                exec_line=exec_line,
                icon=self._prepare_icon(),
                comment=self.comment_edit.text().strip(),
                categories=[self.category.currentData()],
                terminal=self.terminal.isChecked(),
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Fehler", f"Der Eintrag konnte nicht angelegt werden:\n{exc}")
            return
        problems = desktop.validate(self.created_path)
        if problems:
            QMessageBox.information(self, "Hinweis", f"Der Eintrag wurde angelegt, die Prüfung meldet aber:\n\n{problems}")
        self.accept()
