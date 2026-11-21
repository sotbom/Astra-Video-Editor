"""Recovery survives an actual child process exiting without window-close cleanup."""

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from app.ui.main_window import MainWindow


def test_recover_after_abrupt_process_exit(qtbot, tmp_path, media_files, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    recovery_dir = tmp_path / "crashed-session"
    code = """
import os, sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.core.media_probe import probe_media

app = QApplication([])
window = MainWindow(recovery_dir=Path(sys.argv[2]))
media_id = window.engine.import_media(probe_media(Path(sys.argv[1])))
clip_id = window.engine.add_clip(media_id, window.session.project.tracks[0].id, 15)
window.engine.split(clip_id, 75)
window.projects.autosave()
timer = QTimer()
def exit_after_save():
    if window.projects.worker is None:
        os._exit(0 if window.projects.recovery_path.is_file() else 2)
timer.timeout.connect(exit_after_save)
timer.start(20)
QTimer.singleShot(15000, lambda: os._exit(3))
app.exec()
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(media_files["video"]), str(recovery_dir)],
        cwd=root,
        env=os.environ.copy(),
        capture_output=True,
        timeout=25,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    recovery = list(recovery_dir.glob("*.astra"))
    assert len(recovery) == 1
    window = MainWindow(recovery_dir=recovery_dir)
    qtbot.addWidget(window)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    window.projects.offer_recovery()
    qtbot.waitUntil(lambda: window.projects.worker is None, timeout=10000)
    assert len(window.session.project.clips) == 2
    assert sorted(c.start for c in window.session.project.clips) == [15, 75]
    assert window.session.dirty
    assert recovery[0].exists()
    path = tmp_path / "recovered-project.astra"
    window.projects.save_path(path)
    qtbot.waitUntil(lambda: window.projects.worker is None, timeout=10000)
    assert path.exists() and not recovery[0].exists()
    assert not window.session.dirty
    window.close()
