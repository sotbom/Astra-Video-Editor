"""Explicit output selection, background progress, cancellation and rendered playback."""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
)

from app.core.render_engine import RenderWorker
from app.export.ffmpeg_builder import ExportSettings


class ExportDialog(QDialog):
    def __init__(self, project, protected=(), parent=None):
        super().__init__(parent)
        self.project, self.protected = project, protected
        self.worker = None
        self.result = None
        self.setWindowTitle("Export timeline")
        self.setMinimumWidth(500)
        layout = QFormLayout(self)
        layout.addRow(
            QLabel(
                "MP4 • H.264 / AAC • CPU encoding\n"
                "Exports the timeline snapshot captured when this dialog opened."
            )
        )
        self.path = QLineEdit()
        self.path.setAccessibleName("Export destination")
        browse = QPushButton("Choose output…")
        browse.clicked.connect(self.choose)
        layout.addRow(self.path, browse)
        self.width, self.height, self.crf = QSpinBox(), QSpinBox(), QSpinBox()
        for spin, value in ((self.width, project.width), (self.height, project.height)):
            spin.setRange(16, 3840)
            spin.setSingleStep(2)
            spin.setValue(value)
        self.crf.setRange(0, 40)
        self.crf.setValue(20)
        layout.addRow("Width (even pixels)", self.width)
        layout.addRow("Height (even pixels)", self.height)
        layout.addRow("CRF quality (lower is better)", self.crf)
        self.burn = QCheckBox("Burn project subtitles into video")
        layout.addRow(self.burn)
        layout.addRow(
            QLabel(f"Frame rate: {project.fps} fps • Aspect ratio preserved with black padding")
        )
        self.progress = QProgressBar()
        self.status = QLabel("Ready")
        self.status.setWordWrap(True)
        self.start = QPushButton("Export")
        self.cancel = QPushButton("Cancel export")
        self.cancel.setEnabled(False)
        self.open_output = QPushButton("Play exported file")
        self.open_output.setEnabled(False)
        self.start.clicked.connect(self.begin)
        self.cancel.clicked.connect(self.cancel_render)
        self.open_output.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.result)))
        )
        for widget in (self.progress, self.status, self.start, self.cancel, self.open_output):
            layout.addRow(widget)
        self.inputs = (self.path, browse, self.width, self.height, self.crf, self.burn, self.start)

    def choose(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export MP4", "Untitled.mp4", "MP4 video (*.mp4)"
        )
        if path:
            self.path.setText(path if Path(path).suffix else path + ".mp4")

    def begin(self):
        if self.worker:
            return
        if not self.path.text().strip():
            self.status.setText("Choose an output filename.")
            return
        settings = ExportSettings(
            self.width.value(), self.height.value(), self.crf.value(), self.burn.isChecked()
        )
        try:
            settings.validate()
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        path = Path(self.path.text()).resolve()
        overwrite = path.exists()
        if (
            overwrite
            and QMessageBox.question(
                self,
                "Replace output?",
                f"Replace {path.name} only after a successful export?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.result = None
        self.open_output.setEnabled(False)
        self.progress.setValue(0)
        self.status.setText("Rendering…")
        for widget in self.inputs:
            widget.setEnabled(False)
        self.cancel.setEnabled(True)
        self.worker = RenderWorker(
            self.project, settings, path, overwrite=overwrite, protected=self.protected, parent=self
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.succeeded.connect(self.completed)
        self.worker.failed.connect(lambda message: self.status.setText(message))
        self.worker.cancelled.connect(
            lambda: self.status.setText("Export cancelled. Existing files preserved.")
        )
        self.worker.finished.connect(self.finished_render)
        self.worker.start()

    def cancel_render(self):
        if self.worker:
            self.worker.cancel_event.set()
            self.status.setText("Cancelling…")
            self.cancel.setEnabled(False)

    def completed(self, path):
        self.result = path
        self.status.setText(f"Export complete: {path}")
        self.open_output.setEnabled(True)

    def finished_render(self):
        worker, self.worker = self.worker, None
        worker.deleteLater()
        for widget in self.inputs:
            widget.setEnabled(True)
        self.cancel.setEnabled(False)

    def reject(self):
        if self.worker:
            self.cancel_render()
        else:
            super().reject()

    def closeEvent(self, event):
        if self.worker:
            self.cancel_render()
            event.ignore()
        else:
            event.accept()
