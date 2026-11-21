"""Subtitle editing, explicit model acquisition and selected-clip transcription."""

import json
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.ai.model_manager import MODELS, installed
from app.ai.transcription import AIWorker
from app.core.project_manager import atomic_write
from app.core.subtitles import Subtitle, SubtitleEngine, SubtitleStyle, export_text, parse_text


class SubtitlePanel(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window, self.session = window, window.session
        self.engine = SubtitleEngine(self.session)
        self.worker = None
        self.setWindowTitle("Subtitles and offline transcription")
        self.resize(850, 700)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Start (ms)", "End (ms)", "Text"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.selected)
        self.table.cellDoubleClicked.connect(self.seek_selected)
        layout.addWidget(self.table, 1)
        form = QFormLayout()
        self.start, self.end = QSpinBox(), QSpinBox()
        for spin in (self.start, self.end):
            spin.setRange(0, 604800000)
        self.end.setValue(2000)
        self.text = QPlainTextEdit()
        self.text.setMaximumHeight(70)
        form.addRow("Start (milliseconds)", self.start)
        form.addRow("End (milliseconds)", self.end)
        form.addRow("Subtitle text", self.text)
        layout.addLayout(form)
        row = QHBoxLayout()
        self.edit_buttons = []
        for title, handler in (
            ("Add", self.add),
            ("Apply", self.apply),
            ("Delete", self.delete),
            ("Split at playhead", self.split),
            ("Merge next", self.merge),
            ("Undo", self.session.undo),
            ("Redo", self.session.redo),
            ("Seek", self.seek_selected),
        ):
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, fn=handler: self.perform(fn))
            row.addWidget(button)
            self.edit_buttons.append(button)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.find, self.replacement = QLineEdit(), QLineEdit()
        self.find.setPlaceholderText("Find literal text")
        self.replacement.setPlaceholderText("Replace with")
        replace_button = QPushButton("Replace all")
        replace_button.clicked.connect(lambda: self.perform(self.replace_all))
        row.addWidget(self.find)
        row.addWidget(self.replacement)
        row.addWidget(replace_button)
        self.edit_buttons.append(replace_button)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.font = QLineEdit(self.session.project.subtitle_style.font)
        self.font.setMaximumWidth(110)
        self.size = QSpinBox()
        self.size.setRange(8, 200)
        self.size.setValue(self.session.project.subtitle_style.size)
        self.color = QLineEdit(self.session.project.subtitle_style.color)
        self.color.setMaximumWidth(90)
        self.outline, self.margin = QSpinBox(), QSpinBox()
        self.outline.setRange(0, 10)
        self.margin.setRange(0, 500)
        self.outline.setValue(self.session.project.subtitle_style.outline)
        self.margin.setValue(self.session.project.subtitle_style.bottom_margin)
        for title, widget in (
            ("Font", self.font),
            ("Size", self.size),
            ("Color", self.color),
            ("Outline", self.outline),
            ("Bottom", self.margin),
        ):
            row.addWidget(QLabel(title))
            row.addWidget(widget)
        style = QPushButton("Apply style")
        style.clicked.connect(lambda: self.perform(self.apply_style))
        row.addWidget(style)
        self.edit_buttons.append(style)
        layout.addLayout(row)
        row = QHBoxLayout()
        for title, handler in (
            ("Import SRT/VTT", self.import_file),
            ("Export SRT/VTT/ASS", self.export_file),
        ):
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, fn=handler: self.perform(fn))
            row.addWidget(button)
            self.edit_buttons.append(button)
        row.addWidget(QLabel("Double-click a row to seek. Export video can burn subtitles in."))
        layout.addLayout(row)
        row = QHBoxLayout()
        self.model = QComboBox()
        for name, (_, detail) in MODELS.items():
            self.model.addItem(f"{name} — {detail}", name)
        self.download = QPushButton("Download selected model")
        self.download.clicked.connect(self.download_model)
        self.model_status = QLabel()
        self.model.currentIndexChanged.connect(self.model_changed)
        row.addWidget(self.model)
        row.addWidget(self.download)
        row.addWidget(self.model_status)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.language = QLineEdit()
        self.language.setPlaceholderText("Language code (blank = auto)")
        self.device = QComboBox()
        self.device.addItems(["cpu", "cuda"])
        self.compute = QComboBox()
        self.compute.addItems(["int8", "float32", "float16", "int8_float16"])
        self.transcribe = QPushButton("Transcribe selected timeline clip")
        self.transcribe.clicked.connect(lambda: self.perform(self.transcribe_clip))
        for widget in (self.language, self.device, self.compute, self.transcribe):
            row.addWidget(widget)
        layout.addLayout(row)
        layout.addWidget(
            QLabel(
                "CPU is the default. CUDA is attempted in isolation "
                "and falls back to CPU on failure."
            )
        )
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status = QLabel("Ready • No model downloads occur during transcription.")
        self.status.setWordWrap(True)
        self.cancel = QPushButton("Cancel AI job")
        self.cancel.setEnabled(False)
        self.cancel.clicked.connect(self.cancel_job)
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        layout.addWidget(self.cancel)
        self.session.changed.connect(self.refresh)
        self.refresh()
        self.model_changed()

    def perform(self, fn):
        try:
            fn()
        except (ValueError, OSError, StopIteration) as exc:
            self.status.setText(str(exc) or "Select a valid subtitle or timeline clip first.")

    def identifier(self):
        row = self.table.currentRow()
        if row < 0:
            raise ValueError("Select a subtitle row.")
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def refresh(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for segment in sorted(self.session.project.subtitles, key=lambda s: s.start_ms):
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, value in enumerate((segment.start_ms, segment.end_ms, segment.text)):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, segment.id)
                self.table.setItem(row, col, item)
        self.table.blockSignals(False)

    def selected(self):
        if self.table.currentRow() >= 0:
            segment = next(s for s in self.session.project.subtitles if s.id == self.identifier())
            self.start.setValue(segment.start_ms)
            self.end.setValue(segment.end_ms)
            self.text.setPlainText(segment.text)

    def add(self):
        self.engine.add(self.start.value(), self.end.value(), self.text.toPlainText())

    def apply(self):
        self.engine.edit(
            self.identifier(), self.start.value(), self.end.value(), self.text.toPlainText()
        )

    def delete(self):
        self.engine.delete(self.identifier())

    def split(self):
        self.engine.split(
            self.identifier(),
            self.session.project.milliseconds(self.window.timeline.playhead.value()),
        )

    def merge(self):
        self.engine.merge(self.identifier())

    def seek_selected(self, *args):
        self.window._timeline_seek(self.session.project.frames(self.start.value()))

    def replace_all(self):
        if not self.find.text():
            raise ValueError("Enter text to find.")
        self.engine.update(
            [
                replace(s, text=s.text.replace(self.find.text(), self.replacement.text()))
                for s in self.session.project.subtitles
            ],
            "Replace subtitle text",
        )

    def apply_style(self):
        self.engine.update(
            self.session.project.subtitles,
            "Subtitle style",
            subtitle_style=SubtitleStyle(
                self.font.text(),
                self.size.value(),
                self.color.text(),
                self.outline.value(),
                self.margin.value(),
            ),
        )

    def import_file(self):
        name, _ = QFileDialog.getOpenFileName(
            self, "Import subtitles", "", "Subtitles (*.srt *.vtt)"
        )
        if name:
            path = Path(name)
            if path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("Subtitle file exceeds 8 MiB.")
            imported = parse_text(path.read_text(encoding="utf-8-sig"), path.suffix[1:].lower())
            self.engine.update((*self.session.project.subtitles, *imported), "Import subtitles")

    def export_file(self):
        name, selected = QFileDialog.getSaveFileName(
            self, "Export subtitles", "Subtitles.srt", "SRT (*.srt);;WebVTT (*.vtt);;ASS (*.ass)"
        )
        if not name:
            return
        path = Path(name).resolve()
        if not path.suffix:
            path = path.with_suffix(
                ".vtt" if "vtt" in selected else ".ass" if "ass" in selected else ".srt"
            )
        protected = [m.info.path for m in self.session.project.media]
        if self.window.projects.path:
            protected.append(self.window.projects.path)
        if any(path == p or (path.exists() and p.exists() and path.samefile(p)) for p in protected):
            raise ValueError("Subtitle export must not overwrite source media or the project.")
        project = self.session.project
        atomic_write(
            path,
            export_text(
                project.subtitles,
                path.suffix[1:].lower(),
                project.subtitle_style,
                project.width,
                project.height,
            ).encode("utf-8"),
        )
        self.status.setText(f"Subtitles exported: {path.name}")

    def model_changed(self):
        self.model_status.setText(
            "Installed" if installed(self.model.currentData()) else "Not installed"
        )

    def download_model(self):
        self.begin({"task": "download", "model": self.model.currentData()})

    def transcribe_clip(self):
        project = self.session.project
        clip = project.clip_by_id(self.window.timeline.selected_id)
        info = project.media_by_id(clip.media_id).info
        if not info.audio_codec:
            raise ValueError("The selected clip contains no audio.")
        if not installed(self.model.currentData()):
            raise ValueError("Download the selected model first.")
        self.offset, self.limit = project.milliseconds(clip.start), project.milliseconds(clip.end)
        self.overlap = [
            s for s in project.subtitles if s.start_ms < self.limit and s.end_ms > self.offset
        ]
        if (
            self.overlap
            and QMessageBox.question(
                self,
                "Replace subtitles in clip?",
                "Successful transcription will replace overlapping subtitle segments "
                "for this clip. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.begin(
            {
                "task": "transcribe",
                "model": self.model.currentData(),
                "device": self.device.currentText(),
                "compute": self.compute.currentText(),
                "language": self.language.text().strip(),
                "source": str(info.path),
                "start_ms": project.milliseconds(clip.source_in),
                "duration_ms": project.milliseconds(clip.duration),
            }
        )

    def begin(self, request):
        if self.worker:
            return
        self.task = request["task"]
        self.worker = AIWorker(request, self)
        self.worker.progress.connect(self.report)
        self.worker.succeeded.connect(self.completed)
        self.worker.failed.connect(lambda message: self.status.setText(message))
        self.worker.cancelled.connect(
            lambda: self.status.setText("AI job cancelled; project preserved.")
        )
        self.worker.finished.connect(self.finished_job)
        for widget in (
            *self.edit_buttons,
            self.table,
            self.download,
            self.transcribe,
            self.model,
            self.device,
            self.compute,
            self.language,
        ):
            widget.setEnabled(False)
        self.cancel.setEnabled(True)
        self.report(-1, "Starting isolated AI process…")
        self.worker.start()

    def report(self, percent, message):
        self.progress.setRange(0, 0 if percent < 0 else 100)
        if percent >= 0:
            self.progress.setValue(percent)
        self.status.setText(message)

    def completed(self, result):
        try:
            if self.task == "transcribe":
                segments = []
                for s in result["segments"]:
                    start = max(self.offset, self.offset + s["start_ms"])
                    end = min(self.limit, self.offset + s["end_ms"])
                    if end > start and s["text"].strip():
                        segments.append(Subtitle(uuid4().hex, start, end, s["text"]))
                if not segments:
                    self.report(100, "No speech found; existing subtitles preserved.")
                    return
                retained = [s for s in self.session.project.subtitles if s not in self.overlap]
                provenance = {k: result[k] for k in ("model", "device", "compute", "language")}
                self.engine.update(
                    (*retained, *segments), "Transcribe clip", transcription=json.dumps(provenance)
                )
                message = f"Added {len(segments)} subtitle segments on {result['device']}."
                if result.get("fallback"):
                    message += " CUDA fallback: " + result["fallback"]
                self.report(100, message)
            else:
                self.report(100, "Model installed. Transcription is now available offline.")
        except (ValueError, KeyError) as exc:
            self.status.setText(f"Transcription result rejected: {exc}")

    def finished_job(self):
        worker, self.worker = self.worker, None
        worker.deleteLater()
        for widget in (
            *self.edit_buttons,
            self.table,
            self.download,
            self.transcribe,
            self.model,
            self.device,
            self.compute,
            self.language,
        ):
            widget.setEnabled(True)
        self.cancel.setEnabled(False)
        self.progress.setRange(0, 100)
        self.model_changed()

    def cancel_job(self):
        if self.worker:
            self.worker.cancel_event.set()
            self.status.setText("Cancelling AI process…")

    def reject(self):
        if self.worker:
            self.cancel_job()
        else:
            super().reject()

    def closeEvent(self, event):
        if self.worker:
            self.cancel_job()
            event.ignore()
        else:
            event.accept()
