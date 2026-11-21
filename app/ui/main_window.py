"""Desktop foundation: asynchronous imports, source library and preview."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QTabWidget,
    QToolBar,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.command_manager import ProjectSession
from app.core.media_probe import MediaInfo
from app.core.timeline_engine import TimelineEngine
from app.media.importer import ImportWorker
from app.ui.audio_panel import AudioPanel
from app.ui.effects_dialog import EffectsDialog
from app.ui.export_dialog import ExportDialog
from app.ui.media_library import MediaLibrary
from app.ui.preview import Preview, timecode
from app.ui.project_actions import ProjectActions
from app.ui.subtitle_panel import SubtitlePanel
from app.ui.timeline import TimelineWidget
from app.ui.timeline_preview import TimelinePreview
from app.version import VERSION


class MainWindow(QMainWindow):
    def __init__(self, recovery_dir: Path | None = None):
        super().__init__()
        self.setWindowTitle(f"Astra Video Editor — {VERSION}")
        self.resize(1280, 800)
        self.setMinimumSize(960, 600)
        self.setAcceptDrops(True)
        self.media: dict[Path, MediaInfo] = {}
        self.pending: set[Path] = set()
        self.worker: ImportWorker | None = None
        self.closing = False
        self.export_dialog = None
        self.subtitle_dialog = None
        self.audio_dialog = None
        self.session = ProjectSession(parent=self)
        self.engine = TimelineEngine(self.session)
        self.projects = ProjectActions(self, self.session, recovery_dir)
        self.library = MediaLibrary()
        self.library.setHeaderLabels(["Media", "Duration"])
        self.library.setRootIsDecorated(False)
        self.library.setAccessibleName("Media library")
        self.library.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.library.currentItemChanged.connect(self._select)
        self.preview = Preview()
        self.preview.failed.connect(self._playback_error)
        self.timeline = TimelineWidget(self.session)
        self.timeline_preview = TimelinePreview(self.session)
        self.timeline_preview.engine.failed.connect(self._playback_error)
        self.timeline.failed.connect(self._playback_error)
        self.timeline.add_requested.connect(self.add_to_timeline)
        self.timeline.seek.connect(self._timeline_seek)
        self.timeline_preview.engine.position_changed.connect(self.timeline.follow_playhead)
        self.monitors = QTabWidget()
        self.monitors.addTab(self.preview, "Source")
        self.monitors.addTab(self.timeline_preview, "Timeline")
        self.monitors.currentChanged.connect(self._monitor_changed)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Select a file to inspect its media properties.")
        self.details.setMaximumHeight(210)
        self.errors = QPlainTextEdit()
        self.errors.setReadOnly(True)
        self.errors.setMaximumHeight(90)
        self.errors.hide()
        left = QWidget()
        column = QVBoxLayout(left)
        heading = QLabel("MEDIA LIBRARY")
        heading.setObjectName("heading")
        column.addWidget(heading)
        column.addWidget(QLabel("Import files or drop them here"))
        column.addWidget(self.library, 1)
        column.addWidget(self.details)
        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(self.monitors)
        splitter.setSizes([340, 940])
        center = QWidget()
        layout = QVBoxLayout(center)
        layout.setContentsMargins(8, 8, 8, 8)
        workspace = QSplitter(Qt.Orientation.Vertical)
        workspace.addWidget(splitter)
        workspace.addWidget(self.timeline)
        workspace.setSizes([450, 300])
        layout.addWidget(workspace, 1)
        layout.addWidget(self.errors)
        self.setCentralWidget(center)
        self._menus()
        self.session.changed.connect(self._project_changed)
        self._project_changed()
        self.statusBar().showMessage("Offline • Ready to import local media")

    def _menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        for label, shortcut, handler in (
            ("New project…", "Ctrl+N", self.projects.new),
            ("Open project…", "Ctrl+O", self.projects.open),
            ("Save project", "Ctrl+S", self.projects.save),
            ("Save project as…", "Ctrl+Shift+S", lambda: self.projects.save(save_as=True)),
        ):
            action = file_menu.addAction(label)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(lambda checked=False, fn=handler: fn())
        file_menu.addAction("Recover autosave…", self.projects.recover)
        file_menu.addAction("Relink selected media…", self.relink_selected)
        self.export_action = file_menu.addAction("Export timeline…", self.export_timeline)
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        file_menu.addSeparator()
        self.import_action = QAction("Import media…", self)
        self.import_action.setShortcut(QKeySequence("Ctrl+I"))
        self.import_action.triggered.connect(self.choose_files)
        file_menu.addAction(self.import_action)
        quit_action = file_menu.addAction("Exit")
        quit_action.setShortcut(QKeySequence("Alt+F4"))
        quit_action.triggered.connect(self.close)
        edit_menu = self.menuBar().addMenu("&Edit")
        self.undo_action = edit_menu.addAction("Undo", self.session.undo)
        self.undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        self.redo_action = edit_menu.addAction("Redo", self.session.redo)
        self.redo_action.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        split_action = edit_menu.addAction("Split selected clip", self.timeline.split)
        split_action.setShortcut(QKeySequence("Ctrl+B"))
        delete_action = edit_menu.addAction("Delete selected clip", self.timeline.delete)
        delete_action.setShortcut(QKeySequence("Ctrl+Delete"))
        edit_menu.addAction("Selected clip video effects…", self.edit_effects)
        subtitles = self.menuBar().addMenu("&Subtitles")
        subtitles.addAction("Edit / transcribe subtitles…", self.edit_subtitles)
        audio_menu = self.menuBar().addMenu("&Audio")
        audio_menu.addAction("Audio Studio…", self.edit_audio)
        playback = self.menuBar().addMenu("&Playback")
        toggle = playback.addAction("Play / Pause")
        toggle.setShortcut(QKeySequence("Space"))
        toggle.triggered.connect(
            lambda: self.preview.toggle()
            if self.monitors.currentIndex() == 0
            else self.timeline_preview.engine.toggle()
        )
        playback.addAction(
            "Stop",
            lambda: self.preview.player.stop()
            if self.monitors.currentIndex() == 0
            else self.timeline_preview.engine.stop(),
        )
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(
            "About Astra",
            lambda: QMessageBox.about(
                self,
                "Astra Video Editor",
                f"Astra Video Editor {VERSION}\nOffline desktop foundation.\n"
                "Non-destructive timeline editing and project files.\n"
                "FFmpeg timeline export and clip video effects.",
            ),
        )
        toolbar = QToolBar("Media tools")
        toolbar.setMovable(False)
        toolbar.addAction(self.import_action)
        self.cancel_action = toolbar.addAction("Cancel import")
        self.cancel_action.setEnabled(False)
        self.cancel_action.triggered.connect(self.cancel_import)
        toolbar.addSeparator()
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)
        toolbar.addAction(self.export_action)
        toolbar.addWidget(QLabel("ASTRA   /   Edit workspace"))
        self.addToolBar(toolbar)

    def choose_files(self) -> None:
        """Open the native multi-file picker."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Import media",
            "",
            "Media (*.mp4 *.mkv *.mov *.avi *.webm *.mp3 *.wav *.flac *.aac *.m4a "
            "*.png *.jpg *.jpeg *.bmp *.webp);;All files (*)",
        )
        self.import_paths(files)

    def edit_effects(self):
        try:
            clip = self.session.project.clip_by_id(self.timeline.selected_id)
            if self.session.project.track_by_id(clip.track_id).kind != "video":
                raise ValueError("Select a video clip for video effects.")
            EffectsDialog(self.engine, clip.id, self).exec()
        except (ValueError, StopIteration) as exc:
            self._import_error("Effects", str(exc) or "Select a timeline video clip first.")

    def edit_subtitles(self):
        self.preview.player.pause()
        self.timeline_preview.engine.pause()
        self.subtitle_dialog = SubtitlePanel(self)
        self.subtitle_dialog.exec()
        self.subtitle_dialog.deleteLater()
        self.subtitle_dialog = None

    def edit_audio(self):
        self.preview.player.pause()
        self.timeline_preview.engine.pause()
        self.audio_dialog = AudioPanel(self)
        self.audio_dialog.exec()
        self.audio_dialog.deleteLater()
        self.audio_dialog = None

    def export_timeline(self):
        self.preview.player.pause()
        self.timeline_preview.engine.pause()
        if self.export_dialog is not None:
            self.export_dialog.show()
            self.export_dialog.raise_()
            return
        protected = (self.projects.path,) if self.projects.path else ()
        self.export_dialog = ExportDialog(self.session.project, protected, self)
        self.export_dialog.setModal(True)
        self.export_dialog.finished.connect(self._export_closed)
        self.export_dialog.show()

    def _export_closed(self):
        dialog, self.export_dialog = self.export_dialog, None
        if dialog:
            dialog.deleteLater()

    def import_paths(self, paths: list[str | Path]) -> None:
        """Deduplicate and enqueue local files without blocking the GUI."""
        if self.closing:
            return
        if self.projects.worker and self.projects.mode in {"open", "recover"}:
            self.statusBar().showMessage("Wait for the project to finish opening.")
            return
        for path in paths:
            resolved = Path(path).resolve()
            if resolved not in self.media:
                self.pending.add(resolved)
        if self.worker is not None:
            return
        self._start_import()

    def _start_import(self) -> None:
        if not self.pending:
            return
        paths = sorted(self.pending - self.media.keys())
        self.pending.clear()
        if not paths:
            return
        self.worker = ImportWorker(paths, self)
        self.worker.imported.connect(self._imported)
        self.worker.failed.connect(self._import_error)
        self.worker.finished.connect(self._finished)
        self.cancel_action.setEnabled(True)
        self.statusBar().showMessage(f"Inspecting {len(paths)} file(s)…")
        self.worker.start()

    @Slot(object)
    def _imported(self, info: MediaInfo) -> None:
        if info.path in self.media or self.closing:
            return
        try:
            self.engine.import_media(info)
        except ValueError as exc:
            self._import_error(info.name, str(exc))

    @Slot()
    def _project_changed(self) -> None:
        current = self.library.currentItem()
        path = current.data(0, Qt.ItemDataRole.UserRole) if current else None
        previous = self.media.get(path)
        self.media = {m.info.path: m.info for m in self.session.project.media}
        self.library.blockSignals(True)
        self.library.clear()
        selected = None
        for info in self.media.values():
            missing = not info.path.is_file()
            item = QTreeWidgetItem(
                [
                    ("[Missing] " if missing else "") + info.name,
                    "Image" if info.is_image else timecode(info.duration_ms),
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, info.path)
            item.setToolTip(0, str(info.path))
            self.library.addTopLevelItem(item)
            if info.path == path:
                selected = item
        selected = selected or self.library.topLevelItem(0)
        self.library.setCurrentItem(selected)
        self.library.blockSignals(False)
        if selected:
            selected_path = selected.data(0, Qt.ItemDataRole.UserRole)
            if path != selected_path or previous != self.media[selected_path]:
                self._select(selected)
        else:
            self.preview.clear()
            self.details.clear()
        self.undo_action.setEnabled(bool(self.session.undo_stack))
        self.redo_action.setEnabled(bool(self.session.redo_stack))
        self.undo_action.setText(
            "Undo " + (self.session.undo_stack[-1].label if self.session.undo_stack else "")
        )
        self.redo_action.setText(
            "Redo " + (self.session.redo_stack[-1].label if self.session.redo_stack else "")
        )
        self.setWindowTitle(
            f"{'* ' if self.session.dirty else ''}{self.session.project.name}"
            f" — Astra Video Editor — {VERSION}"
        )

    def add_to_timeline(self, track_id: str, frame: int) -> None:
        item = self.library.currentItem()
        if not item:
            self._import_error("Timeline", "Select a source in the media library first.")
            return
        try:
            media_id = self.engine.media_id_for_path(item.data(0, Qt.ItemDataRole.UserRole))
            clip_id = self.engine.add_clip(media_id, track_id, frame)
            self.timeline.select_clip(clip_id)
            self.timeline.view.redraw()
            self.monitors.setCurrentIndex(1)
        except ValueError as exc:
            self._import_error("Timeline", str(exc))

    def _timeline_seek(self, frame: int) -> None:
        self.monitors.setCurrentIndex(1)
        self.timeline_preview.engine.seek(frame)

    def _monitor_changed(self, index: int) -> None:
        if index == 0:
            self.timeline_preview.engine.pause()
        else:
            self.preview.player.pause()

    def relink_selected(self) -> None:
        if self.worker or self.projects.worker or not self.library.currentItem():
            return
        path = self.library.currentItem().data(0, Qt.ItemDataRole.UserRole)
        name, _ = QFileDialog.getOpenFileName(
            self, "Choose replacement source", "", "All files (*)"
        )
        if not name:
            return
        self.relink_id = self.engine.media_id_for_path(path)
        self.worker = ImportWorker([Path(name)], self)
        self.worker.imported.connect(self._relinked)
        self.worker.failed.connect(self._import_error)
        self.worker.finished.connect(self._finished)
        self.worker.start()

    @Slot(object)
    def _relinked(self, info: MediaInfo) -> None:
        try:
            self.engine.relink(self.relink_id, info)
        except ValueError as exc:
            self._import_error("Relink", str(exc))

    def _select(self, item, previous=None) -> None:
        if item is None:
            return
        info = self.media[item.data(0, Qt.ItemDataRole.UserRole)]
        self.details.setPlainText(
            f"{info.name}\n\nDuration: {timecode(info.duration_ms)}\n"
            f"Video: {info.video_codec or 'None'}\n"
            f"Resolution: {info.width} × {info.height}\n"
            f"Frame rate: {info.fps} ({float(info.fps):.3f} fps)\n"
            f"Audio: {info.audio_codec or 'None'} · {info.channels} channel(s)"
            f" · {info.sample_rate} Hz\n\n{info.path}"
        )
        if info.path.is_file():
            self.preview.load(info)
        else:
            self.preview.clear()

    @Slot(str, str)
    def _import_error(self, name: str, message: str) -> None:
        logging.getLogger(__name__).warning("Media operation failed; details shown in the UI")
        self.errors.show()
        self.errors.appendPlainText(f"{name}: {message}")
        self.errors.document().setMaximumBlockCount(100)

    def _playback_error(self, message: str) -> None:
        self._import_error("Preview", message)

    @Slot()
    def _finished(self) -> None:
        worker, self.worker = self.worker, None
        if worker:
            worker.deleteLater()
        self.cancel_action.setEnabled(False)
        self.statusBar().showMessage(f"Offline • {len(self.media)} file(s) in library")
        if self.closing:
            QTimer.singleShot(0, self.close)
        else:
            self._start_import()

    def cancel_import(self) -> None:
        """Cancel queued files; the current probe has a bounded timeout."""
        self.pending.clear()
        if self.worker:
            self.worker.cancelled.set()
            self.statusBar().showMessage("Cancelling after the current file…")

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() and all(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        self.import_paths([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])
        event.acceptProposedAction()

    def closeEvent(self, event) -> None:
        if self.audio_dialog and (
            self.audio_dialog.worker
            or self.audio_dialog.wave_worker
            or self.audio_dialog.analysis_worker
        ):
            self.audio_dialog.cancel_job()
            event.ignore()
            return
        if self.subtitle_dialog and self.subtitle_dialog.worker:
            self.subtitle_dialog.cancel_job()
            event.ignore()
            return
        if self.export_dialog and self.export_dialog.worker:
            self.export_dialog.cancel_render()
            event.ignore()
            return
        self.preview.player.stop()
        self.timeline_preview.engine.pause()
        if self.worker is not None:
            self.closing = True
            self.cancel_import()
            event.ignore()
        else:
            if self.projects.confirm_close():
                self.timeline_preview.engine.shutdown()
                event.accept()
            else:
                self.closing = False
                event.ignore()
