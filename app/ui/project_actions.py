"""Desktop project lifecycle, asynchronous persistence, autosave and recovery prompts."""

import os
from pathlib import Path

from PySide6.QtCore import QObject, QStandardPaths, QTimer, Slot
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from app.core.project_manager import ProjectIOWorker
from app.core.project_schema import Project, new_id


class ProjectActions(QObject):
    def __init__(self, window, session, recovery_dir: Path | None = None):
        super().__init__(window)
        self.window, self.session = window, session
        self.path: Path | None = None
        data_dir = Path(
            os.environ.get("ASTRA_DATA_DIR")
            or QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        )
        self.recovery_dir = recovery_dir or data_dir / "recovery"
        self.recovery_path = self.recovery_dir / f"{new_id()}.astra"
        self.recovered_from: Path | None = None
        self.autosaved = None
        self.worker = None
        self.result = None
        self.continuation = None
        self.close_pending = False
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(30000)
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_timer.start()

    def _ready(self) -> bool:
        if self.worker or self.window.worker:
            self.window.statusBar().showMessage("Wait for the current import or project operation.")
            return False
        return True

    def _confirm(self):
        return QMessageBox.question(
            self.window,
            "Unsaved project",
            "Save changes before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )

    def transition(self, action) -> None:
        if not self._ready():
            return
        if self.session.dirty:
            choice = self._confirm()
            if choice == QMessageBox.StandardButton.Cancel:
                return
            if choice == QMessageBox.StandardButton.Save:
                self.save(on_success=lambda: self.transition(action))
                return
        action()

    def new(self) -> None:
        def create():
            name, accepted = QInputDialog.getText(self.window, "New project", "Project name:")
            if not accepted or not name.strip():
                return
            fps, accepted = QInputDialog.getItem(
                self.window,
                "Project frame rate",
                "Frame rate:",
                ["24", "25", "30", "30000/1001", "60"],
                2,
                False,
            )
            if accepted:
                from fractions import Fraction

                rate = Fraction(fps)
                self.replace_project(
                    Project(
                        name=name.strip()[:200], fps_num=rate.numerator, fps_den=rate.denominator
                    )
                )

        self.transition(create)

    def replace_project(
        self, project: Project, path: Path | None = None, recovered: bool = False
    ) -> None:
        self.clear_recovery(preserve=self.operation_path if recovered else None)
        self.path = path
        self.autosaved = None
        self.window.preview.clear()
        self.window.library.clear()
        self.session.reset(project, recovered)
        self.window.timeline.follow_playhead(0)
        self.window.timeline_preview.engine.seek(0)
        missing = project.missing_media()
        if missing:
            self.window._import_error(
                "Project",
                f"{len(missing)} source file(s) missing. "
                "Select each missing item and use File → Relink selected media.",
            )

    def open(self) -> None:
        if not self._ready():
            return
        name, _ = QFileDialog.getOpenFileName(
            self.window,
            "Open Astra project",
            "",
            "Astra project (*.astra);;Project backup (*.astra.bak)",
        )
        if name:
            self.open_path(Path(name))

    def open_path(self, path: Path, recovered: bool = False) -> None:
        self.transition(lambda: self._start("recover" if recovered else "open", path))

    def save(self, save_as: bool = False, on_success=None) -> bool:
        if not self._ready():
            return False
        path = self.path
        if save_as or path is None:
            name, _ = QFileDialog.getSaveFileName(
                self.window,
                "Save Astra project",
                str(path or "Untitled.astra"),
                "Astra project (*.astra)",
            )
            if not name:
                return False
            path = Path(name)
            if path.suffix.lower() != ".astra":
                path = path.with_suffix(path.suffix + ".astra")
        return self.save_path(path, on_success=on_success)

    def save_path(self, path: Path, on_success=None) -> bool:
        if not self._ready():
            return False
        self.continuation = on_success
        self._start("save", path, self.session.project)
        return True

    def autosave(self) -> None:
        if (
            self.worker
            or self.window.worker
            or not self.session.dirty
            or self.autosaved == self.session.project
        ):
            return
        self._start("autosave", self.recovery_path, self.session.project)

    def _start(self, mode: str, path: Path, snapshot=None) -> None:
        self.mode = mode
        self.result = None
        self.operation_path = path.resolve()
        if mode in {"open", "recover"}:
            self.window.setEnabled(False)
        self.worker = ProjectIOWorker(path, snapshot, backup=mode != "autosave", parent=self)
        self.worker.succeeded.connect(self._succeeded)
        self.worker.failed.connect(self._failed)
        self.worker.finished.connect(self._finished)
        self.window.statusBar().showMessage(f"Project {mode} in progress…")
        self.worker.start()

    @Slot(object)
    def _succeeded(self, result) -> None:
        self.result = result

    @Slot(str)
    def _failed(self, message: str) -> None:
        self.window._import_error("Project", message)
        self.window.statusBar().showMessage("Project operation failed; existing project preserved")

    @Slot()
    def _finished(self) -> None:
        worker, self.worker = self.worker, None
        worker.deleteLater()
        self.window.setEnabled(True)
        result = self.result
        continuation, self.continuation = self.continuation, None
        if result is not None:
            if self.mode == "save":
                self.path = self.operation_path
                self.session.mark_saved(result)
                if not self.session.dirty:
                    self.clear_recovery()
            elif self.mode == "autosave":
                self.autosaved = result
            else:
                recovered = self.mode == "recover"
                self.replace_project(result, None if recovered else self.operation_path, recovered)
                if recovered:
                    self.recovered_from = self.operation_path
            self.window.statusBar().showMessage(
                "Recovery copy saved"
                if self.mode == "autosave"
                else f"Project {self.mode} complete"
            )
            if continuation:
                QTimer.singleShot(0, continuation)
        if self.close_pending:
            self.close_pending = False
            QTimer.singleShot(0, self.window.close)

    def clear_recovery(self, preserve: Path | None = None) -> None:
        """Remove only this session's recovery after a save or explicit discard."""
        for path in (self.recovery_path, self.recovered_from):
            if path and path != preserve:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    self.window._import_error("Recovery", "Could not remove an old recovery copy.")
        self.recovered_from = None
        self.autosaved = None

    def recover(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self.window, "Recover autosave", str(self.recovery_dir), "Astra recovery (*.astra)"
        )
        if name:
            self.open_path(Path(name), recovered=True)

    def offer_recovery(self) -> None:
        """Startup recovery is opt-in; declining preserves all previous recovery files."""
        candidates = sorted(self.recovery_dir.glob("*.astra"), key=lambda p: p.stat().st_mtime)
        if (
            candidates
            and QMessageBox.question(
                self.window,
                "Recovery available",
                "Recover the most recent unsaved session?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.open_path(candidates[-1], recovered=True)

    def confirm_close(self) -> bool:
        if self.worker:
            self.close_pending = True
            return False
        if self.session.dirty:
            choice = self._confirm()
            if choice == QMessageBox.StandardButton.Cancel:
                return False
            if choice == QMessageBox.StandardButton.Save:
                self.save(on_success=self.window.close)
                return False
        self.clear_recovery()
        self.autosave_timer.stop()
        return True
