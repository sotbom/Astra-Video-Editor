from dataclasses import replace

import pytest
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QMessageBox

from app.core.media_probe import probe_media
from app.core.project_manager import load_project, save_project
from app.core.project_schema import Project
from app.ui.main_window import MainWindow
from app.ui.timeline import LEFT, MEDIA_MIME, TOP


@pytest.fixture
def editor(qtbot, media_files):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.import_paths([media_files["video"]])
    qtbot.waitUntil(lambda: window.worker is None and len(window.media) == 1, timeout=30000)
    yield window
    window.close()


def test_add_split_trim_move_delete_and_undo_ui(editor, qtbot):
    window = editor
    timeline = window.timeline
    qtbot.mouseClick(timeline.add_button, Qt.MouseButton.LeftButton)
    original = window.session.project
    assert len(original.clips) == 1
    timeline.playhead.setValue(60)
    qtbot.mouseClick(timeline.split_button, Qt.MouseButton.LeftButton)
    assert len(window.session.project.clips) == 2
    right_id = timeline.selected_id
    timeline.start.setValue(90)
    timeline.source_in.setValue(75)
    timeline.source_out.setValue(150)
    qtbot.mouseClick(timeline.apply_button, Qt.MouseButton.LeftButton)
    assert window.session.project.clip_by_id(right_id).start == 90
    edited = window.session.project
    window.undo_action.trigger()
    window.undo_action.trigger()
    assert window.session.project == original
    window.redo_action.trigger()
    window.redo_action.trigger()
    assert window.session.project == edited
    timeline.select_clip(right_id)
    qtbot.mouseClick(timeline.delete_button, Qt.MouseButton.LeftButton)
    assert len(window.session.project.clips) == 1
    window.undo_action.trigger()
    assert window.session.project == edited
    assert window.errors.toPlainText() == ""


def test_canvas_drag_move_and_edge_trim(editor, qtbot):
    editor.timeline.add_button.click()
    view = editor.timeline.view
    view.snap = False
    clip_id = editor.session.project.clips[0].id
    start = view.mapFromScene(QPointF(LEFT + 60 * view.scale_x, TOP + 20))
    end = view.mapFromScene(QPointF(LEFT + 90 * view.scale_x, TOP + 20))
    qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(view.viewport(), end)
    qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)
    assert editor.session.project.clip_by_id(clip_id).start == 30
    start = view.mapFromScene(QPointF(LEFT + 30 * view.scale_x + 2, TOP + 20))
    end = view.mapFromScene(QPointF(LEFT + 45 * view.scale_x + 2, TOP + 20))
    qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(view.viewport(), end)
    qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)
    clip = editor.session.project.clip_by_id(clip_id)
    assert (clip.start, clip.source_in, clip.source_out) == (45, 15, 180)


def test_drop_clip_and_create_gap(editor, qtbot):
    from PySide6.QtWidgets import QApplication

    mime = editor.library.mimeData([editor.library.currentItem()])
    assert mime.hasFormat(MEDIA_MIME)
    view = editor.timeline.view
    point = view.mapFromScene(QPointF(LEFT + 30 * view.scale_x, TOP + 20))
    enter = QDragEnterEvent(
        point,
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(view.viewport(), enter)
    assert enter.isAccepted()
    drop = QDropEvent(
        QPointF(point),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(view.viewport(), drop)
    assert drop.isAccepted()
    assert editor.session.project.clips[0].start == 30
    editor.timeline.playhead.setValue(240)
    assert editor.timeline.playhead.value() == 240
    editor.timeline.add_button.click()
    assert len(editor.session.project.clips) == 2
    assert editor.session.project.end == 420


def test_timeline_real_playback_cuts_gap_and_stop(editor, qtbot):
    editor.timeline.add_button.click()
    project = editor.session.project
    first = project.clips[0]
    editor.engine.edit_clip(first.id, start=0, source_in=30, source_out=60)
    second_id = editor.engine.add_clip(first.media_id, first.track_id, 45)
    editor.engine.edit_clip(second_id, start=45, source_in=90, source_out=120)
    monitor = editor.timeline_preview
    playback = monitor.engine
    frames = []
    monitor.video.videoSink().videoFrameChanged.connect(
        lambda frame: frames.append(frame.toImage()) if frame.isValid() else None,
        Qt.ConnectionType.QueuedConnection,
    )
    playback.seek(0)
    monitor.play.click()
    qtbot.waitUntil(lambda: playback.frame >= 8 and len(frames) > 2, timeout=15000)
    assert any(not frame.isNull() for frame in frames)
    assert frames[0] != frames[-1]
    playback.pause()
    at_pause = playback.frame
    qtbot.wait(120)
    assert playback.frame == at_pause
    playback.seek(35)
    assert monitor.stack.currentWidget() == monitor.still
    assert "No video" in monitor.still.text()
    playback.seek(50)
    stream = playback.streams[first.track_id]
    assert stream.clip_id == second_id
    qtbot.waitUntil(
        lambda: abs(stream.player.position() - project.milliseconds(95)) < 100, timeout=5000
    )
    playback.play()
    qtbot.waitUntil(lambda: not playback.playing and playback.frame == 75, timeout=10000)
    monitor.stop.click()
    assert playback.frame == 0
    assert not playback.playing


def test_track_mute_hide_lock_and_audio_playback(editor, media_files, qtbot):
    editor.timeline.add_button.click()
    project = editor.session.project
    video_track = project.tracks[0].id
    audio_track = project.tracks[1].id
    audio_id = editor.engine.import_media(probe_media(media_files["audio"]))
    editor.engine.add_clip(audio_id, audio_track, 0)
    playback = editor.timeline_preview.engine
    playback.play()
    qtbot.waitUntil(lambda: playback.streams[audio_track].player.position() > 200, timeout=10000)
    editor.engine.set_track(audio_track, muted=True)
    assert playback.streams[audio_track].audio.isMuted()
    editor.engine.set_track(video_track, hidden=True, locked=True)
    assert editor.timeline_preview.stack.currentWidget() == editor.timeline_preview.still
    old = editor.session.project
    editor.timeline.select_clip(old.clips[0].id)
    editor.timeline.delete_button.click()
    assert editor.session.project == old
    assert "Unlock" in editor.errors.toPlainText()


def test_video_track_handoff_and_still_image(editor, media_files, qtbot):
    editor.timeline.add_button.click()
    first = editor.session.project.clips[0]
    editor.engine.edit_clip(first.id, start=0, source_in=0, source_out=15)
    lower = editor.engine.add_track("video")
    editor.engine.add_clip(first.media_id, lower, 0)
    image_id = editor.engine.import_media(probe_media(media_files["image"]))
    editor.engine.add_clip(image_id, first.track_id, 30)
    monitor = editor.timeline_preview
    playback = monitor.engine
    playback.play()
    qtbot.waitUntil(lambda: playback.frame >= 20, timeout=10000)
    assert playback.visual_track == lower
    assert playback.streams[lower].player.videoOutput() == monitor.video
    qtbot.waitUntil(lambda: playback.frame >= 35, timeout=10000)
    assert playback.visual_track == first.track_id
    assert monitor.stack.currentWidget() == monitor.still
    assert not monitor.still.pixmap().isNull()
    playback.stop()
    assert playback.frame == 0
    assert playback.streams[first.track_id].player.videoOutput() == monitor.video


def test_save_reopen_autosave_and_recovery(editor, qtbot, tmp_path):
    editor.timeline.add_button.click()
    expected = editor.session.project
    ticks = []
    timer = QTimer(editor)
    timer.setInterval(1)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    path = tmp_path / "edited project.astra"
    editor.projects.save_path(path)
    qtbot.waitUntil(lambda: editor.projects.worker is None, timeout=10000)
    assert ticks
    assert not editor.session.dirty
    assert load_project(path) == expected
    editor.engine.split(expected.clips[0].id, 60)
    edited = editor.session.project
    editor.projects.autosave()
    qtbot.waitUntil(lambda: editor.projects.worker is None, timeout=10000)
    recovery = editor.projects.recovery_path
    assert load_project(recovery) == edited
    # Model abrupt loss of in-memory state using an independently opened recovery file.
    copy = tmp_path / "crash-recovery.astra"
    save_project(load_project(recovery), copy, backup=False)
    editor.projects.open_path(path)
    qtbot.waitUntil(lambda: editor.projects.worker is None, timeout=10000)
    assert editor.session.project == expected
    assert not editor.session.dirty
    editor.projects.open_path(copy, recovered=True)
    qtbot.waitUntil(lambda: editor.projects.worker is None, timeout=10000)
    assert editor.session.project == edited
    assert editor.session.dirty
    assert copy.exists(), "Recovery must survive until an explicit save or discard"
    editor.projects.save_path(tmp_path / "recovered.astra")
    qtbot.waitUntil(lambda: editor.projects.worker is None, timeout=10000)
    assert not copy.exists()
    assert not editor.session.dirty


def test_cancel_close_and_cancel_open_keep_edits(editor, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Cancel)
    project = editor.session.project
    editor.close()
    assert editor.isVisible()
    path = tmp_path / "other.astra"
    save_project(Project(), path)
    editor.projects.open_path(path)
    assert editor.projects.worker is None
    assert editor.session.project == project
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Discard)


def test_malformed_open_and_save_failure_preserve_project(editor, qtbot, tmp_path, monkeypatch):
    import app.core.project_manager as manager

    before = editor.session.project
    path = tmp_path / "bad.astra"
    path.write_text('{"schema_version": 999}')
    editor.projects.open_path(path)
    qtbot.waitUntil(lambda: editor.projects.worker is None, timeout=10000)
    assert editor.session.project == before
    assert editor.session.dirty
    assert editor.centralWidget().isEnabled()
    assert "Project:" in editor.errors.toPlainText()

    def fail_write(*args):
        raise OSError("Simulated full disk")

    monkeypatch.setattr(manager, "atomic_write", fail_write)
    editor.projects.save_path(tmp_path / "failed.astra")
    qtbot.waitUntil(lambda: editor.projects.worker is None, timeout=10000)
    assert editor.session.project == before
    assert editor.session.dirty
    assert "full disk" in editor.errors.toPlainText()


def test_missing_media_relink_workflow(editor, media_files, qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    editor.timeline.add_button.click()
    project = editor.session.project
    media = project.media[0]
    missing = replace(media, info=replace(media.info, path=tmp_path / "missing.mp4"))
    editor.projects.replace_project(replace(project, media=(missing,)))
    assert "[Missing]" in editor.library.topLevelItem(0).text(0)
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args: (str(media_files["video"]), "")
    )
    editor.relink_selected()
    qtbot.waitUntil(lambda: editor.worker is None, timeout=30000)
    assert not editor.session.project.missing_media()
    assert editor.session.project.clips == project.clips
    assert "[Missing]" not in editor.library.topLevelItem(0).text(0)
