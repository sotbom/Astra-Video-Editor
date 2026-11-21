"""Library drag payloads contain local paths already present in the project."""

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtWidgets import QTreeWidget

from app.ui.timeline import MEDIA_MIME


class MediaLibrary(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)

    def mimeData(self, items):
        mime = QMimeData()
        if items:
            path = items[0].data(0, Qt.ItemDataRole.UserRole)
            mime.setData(MEDIA_MIME, str(path).encode("utf-8"))
        return mime
