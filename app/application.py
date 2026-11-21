"""Application lifetime and logging setup."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QTimer
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme import STYLESHEET


def run() -> int:
    """Run the desktop application and optionally import command-line paths."""
    application = QApplication(sys.argv)
    application.setApplicationName("Astra Video Editor")
    application.setOrganizationName("Astra")
    application.setStyle("Fusion")
    application.setStyleSheet(STYLESHEET)
    log_dir = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[RotatingFileHandler(log_dir / "astra.log", maxBytes=1_000_000, backupCount=2)],
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    window = MainWindow()
    window.show()
    if len(sys.argv) == 2 and sys.argv[1].lower().endswith((".astra", ".astra.bak")):
        QTimer.singleShot(0, lambda: window.projects.open_path(Path(sys.argv[1])))
    elif len(sys.argv) > 1:
        QTimer.singleShot(0, lambda: window.import_paths(sys.argv[1:]))
    else:
        QTimer.singleShot(0, window.projects.offer_recovery)
    logging.info("Desktop application started")
    return application.exec()
