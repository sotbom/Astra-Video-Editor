"""Exercise connected effect/export controls against real FFmpeg and Qt playback."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMessageBox

from app.core.media_probe import probe_media
from app.core.project_schema import Project
from app.ui.effects_dialog import EffectsDialog
from app.ui.export_dialog import ExportDialog
from app.ui.main_window import MainWindow
from app.video.filters import VideoEffects


def test_effect_dialog_export_progress_and_decoded_playback(qtbot, media_files, tmp_path):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    media_id = window.engine.import_media(probe_media(media_files["video"]))
    clip = window.engine.add_clip(media_id, window.session.project.tracks[0].id, 0)
    window.engine.edit_clip(clip, start=0, source_in=30, source_out=60)
    dialog = EffectsDialog(window.engine, clip, window)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.controls["negative"].setChecked(True)
    dialog.controls["crop_left"].setValue(20)
    dialog.apply()
    assert window.session.project.clip_by_id(clip).effects.negative
    window.undo_action.trigger()
    assert window.session.project.clip_by_id(clip).effects == VideoEffects()
    window.redo_action.trigger()
    window.export_action.trigger()
    export = window.export_dialog
    export.width.setValue(320)
    export.height.setValue(180)
    output = tmp_path / "ui export.mp4"
    export.path.setText(str(output))
    ticks = []
    timer = QTimer(window)
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(export.worker is not None))
    timer.start()
    qtbot.mouseClick(export.start, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: export.worker is None, timeout=30000)
    assert export.result == output
    assert export.progress.value() == 100 and export.open_output.isEnabled()
    assert any(ticks), "The event loop must run while encoding is active"
    export.reject()
    qtbot.waitUntil(lambda: window.export_dialog is None)
    frames = []
    window.preview.video.videoSink().videoFrameChanged.connect(
        lambda f: frames.append(f.toImage()) if f.isValid() else None,
        Qt.ConnectionType.QueuedConnection,
    )
    window.preview.load(probe_media(output))
    window.preview.toggle()
    qtbot.waitUntil(lambda: len(frames) > 3, timeout=10000)
    assert frames[0] != frames[-1]
    window.preview.player.stop()
    window.close()


def test_cancel_running_export_keeps_existing_output(qtbot, media_files, tmp_path, monkeypatch):
    from app.core.command_manager import ProjectSession
    from app.core.timeline_engine import TimelineEngine

    session = ProjectSession()
    engine = TimelineEngine(session)
    media = engine.import_media(probe_media(media_files["image"]))
    clip = engine.add_clip(media, session.project.tracks[0].id, 0)
    engine.edit_clip(clip, start=0, source_in=0, source_out=18000)
    output = tmp_path / "existing.mp4"
    output.write_bytes(b"original output")
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.StandardButton.Yes)
    dialog = ExportDialog(session.project)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.path.setText(str(output))
    dialog.begin()
    qtbot.waitUntil(
        lambda: bool(list(tmp_path.glob(".astra-render-*/progress.txt"))), timeout=15000
    )
    dialog.reject()  # Closing while active cancels and retains the dialog until safe.
    assert dialog.isVisible()
    qtbot.waitUntil(lambda: dialog.worker is None, timeout=15000)
    assert "cancelled" in dialog.status.text()
    assert output.read_bytes() == b"original output"
    assert not list(tmp_path.glob(".astra-render-*"))
    assert dialog.start.isEnabled()
    dialog.reject()


def test_export_failure_and_invalid_settings_are_visible(qtbot, tmp_path):
    dialog = ExportDialog(Project())
    qtbot.addWidget(dialog)
    dialog.path.setText(str(tmp_path / "empty.mp4"))
    dialog.width.setValue(321)
    dialog.begin()
    assert "even" in dialog.status.text()
    assert dialog.worker is None
    dialog.width.setValue(320)
    dialog.begin()
    qtbot.waitUntil(lambda: dialog.worker is None, timeout=10000)
    assert "at least one" in dialog.status.text()
    assert not dialog.open_output.isEnabled()


def test_effect_dialog_rejects_crop_without_changing_project(qtbot, media_files, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)
    media = window.engine.import_media(probe_media(media_files["image"]))
    clip = window.engine.add_clip(media, window.session.project.tracks[0].id, 0)
    before = window.session.project
    dialog = EffectsDialog(window.engine, clip, window)
    qtbot.addWidget(dialog)
    errors = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: errors.append(args[2]))
    dialog.controls["crop_left"].setValue(320)
    dialog.apply()
    assert errors and window.session.project == before
    dialog.reset()
    dialog.apply()
    assert window.session.project == before
    window.close()


def test_mask_editor_background_preview(qtbot, media_files):
    from app.video.masks import Mask

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    media = window.engine.import_media(probe_media(media_files["video"]))
    clip = window.engine.add_clip(media, window.session.project.tracks[0].id, 0)
    dialog = EffectsDialog(window.engine, clip, window)
    qtbot.addWidget(dialog)
    dialog.show()
    editor = dialog.mask_editor
    for shape in ("rectangle", "ellipse", "polygon", "freehand"):
        editor.load(
            Mask(
                shape=shape,
                points=((0.2, 0.2), (0.8, 0.2), (0.5, 0.8))
                if shape in ("polygon", "freehand")
                else (),
            )
        )
        editor.controls["width"].setValue(0.4)
        editor.controls["feather"].setValue(15)
        editor.controls["strength"].setValue(0.5)
        editor.inverted.setChecked(True)
        dialog.preview()
        qtbot.waitUntil(lambda: dialog.worker is None, timeout=40000)
        assert not editor.canvas.image.isNull(), dialog.status.text()
    from pathlib import Path

    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QTabWidget

    dialog.findChild(QTabWidget).setCurrentIndex(1)
    editor.shape.setCurrentText("rectangle")
    qtbot.mousePress(editor.canvas, Qt.MouseButton.LeftButton, pos=QPoint(30, 30))
    qtbot.mouseMove(editor.canvas, QPoint(250, 150))
    qtbot.mouseRelease(editor.canvas, Qt.MouseButton.LeftButton, pos=QPoint(250, 150))
    assert editor.canvas.mask.width > 0.3
    editor.shape.setCurrentText("polygon")
    for point in (QPoint(40, 40), QPoint(300, 40), QPoint(170, 200)):
        qtbot.mouseClick(editor.canvas, Qt.MouseButton.LeftButton, pos=point)
    assert len(editor.canvas.mask.points) == 3
    editor.shape.setCurrentText("freehand")
    qtbot.mousePress(editor.canvas, Qt.MouseButton.LeftButton, pos=QPoint(40, 40))
    for point in (QPoint(300, 40), QPoint(170, 200), QPoint(40, 40)):
        qtbot.mouseMove(editor.canvas, point)
    qtbot.mouseRelease(editor.canvas, Qt.MouseButton.LeftButton, pos=QPoint(40, 40))
    assert len(editor.canvas.mask.points) >= 3
    dialog.preview()
    qtbot.waitUntil(lambda: dialog.worker is None, timeout=40000)
    qtbot.wait(100)
    dialog.grab().save(str(Path("artifacts/phase7-editor.png").resolve()))
    dialog.apply()
    assert window.session.project.clip_by_id(clip).effects.mask.shape == "freehand"
    window.close()
