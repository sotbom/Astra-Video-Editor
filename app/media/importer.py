"""Sequential, cancellable background inspection with GUI-thread delivery."""

from pathlib import Path
from threading import Event

from PySide6.QtCore import QThread, Signal

from app.core.media_probe import MediaError, probe_media


class ImportWorker(QThread):
    imported = Signal(object)
    failed = Signal(str, str)

    def __init__(self, paths: list[Path], parent=None):
        super().__init__(parent)
        self.paths = paths
        self.cancelled = Event()

    def run(self) -> None:
        """Probe outside the GUI; cancellation takes effect between files."""
        for path in self.paths:
            if self.cancelled.is_set():
                break
            try:
                self.imported.emit(probe_media(path))
            except MediaError as exc:
                self.failed.emit(path.name, str(exc))
