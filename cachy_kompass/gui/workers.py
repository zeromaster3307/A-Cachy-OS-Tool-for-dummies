"""Hintergrundaufgaben, damit die Oberfläche beim Einlesen nicht einfriert."""

from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class TaskSignals(QObject):
    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)


class Task(QRunnable):
    """Führt ``fn(progress=…)`` in einem Hintergrund-Thread aus.

    Die Signale landen automatisch im Hauptthread, weil ``TaskSignals`` dort
    erzeugt wurde – die Oberfläche darf sie also direkt verarbeiten.
    """

    def __init__(self, fn: Callable[..., Any], *args: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.signals = TaskSignals()

    def run(self) -> None:
        try:
            result = self.fn(*self.args, progress=self.signals.progress.emit)
        except Exception:
            self.signals.failed.emit(traceback.format_exc())
        else:
            self.signals.finished.emit(result)


class TaskRunner:
    """Hält laufende Aufgaben fest, damit Python sie nicht vorzeitig aufräumt."""

    def __init__(self) -> None:
        self._pool = QThreadPool.globalInstance()
        self._running: set[Task] = set()

    def start(
        self,
        fn: Callable[..., Any],
        *args: Any,
        on_done: Callable[[Any], None],
        on_error: Callable[[str], None],
        on_progress: Callable[[str], None],
    ) -> None:
        task = Task(fn, *args)
        task.setAutoDelete(False)
        task.signals.progress.connect(on_progress)
        task.signals.finished.connect(on_done)
        task.signals.failed.connect(on_error)
        task.signals.finished.connect(lambda _: self._running.discard(task))
        task.signals.failed.connect(lambda _: self._running.discard(task))
        self._running.add(task)
        self._pool.start(task)

    @property
    def busy(self) -> bool:
        return bool(self._running)
