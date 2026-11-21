from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtMultimedia import QMediaPlayer

from app.ui.main_window import MainWindow


def test_import_play_pause_seek_stop(qtbot, media_files):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    ticks = []
    timer = QTimer(window)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(10)
    window.import_paths([media_files["video"], media_files["video"]])
    qtbot.waitUntil(lambda: window.worker is None and len(window.media) == 1, timeout=30000)
    assert ticks, "GUI event loop must remain live during import"
    assert window.library.topLevelItemCount() == 1
    assert "640 × 360" in window.details.toPlainText()
    player = window.preview.player
    frames = []
    window.preview.video.videoSink().videoFrameChanged.connect(
        lambda frame: frames.append(frame.toImage()) if frame.isValid() else None,
        Qt.ConnectionType.QueuedConnection,
    )
    qtbot.waitUntil(lambda: player.duration() > 0, timeout=15000)
    qtbot.mouseClick(window.preview.play, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: player.position() > 600 and len(frames) >= 3, timeout=15000)
    assert any(not frame.isNull() and frame.width() == 640 for frame in frames)
    assert frames[0] != frames[-1], "Decoded video frames must actually change"
    qtbot.mouseClick(window.preview.play, Qt.MouseButton.LeftButton)
    assert player.playbackState() == QMediaPlayer.PlaybackState.PausedState
    paused = player.position()
    qtbot.wait(200)
    assert abs(player.position() - paused) < 100
    window.preview.seek.setValue(3000)
    window.preview.seek.sliderReleased.emit()
    qtbot.waitUntil(lambda: abs(player.position() - 3000) < 200, timeout=5000)
    window.preview.volume.setValue(25)
    assert abs(window.preview.audio.volume() - 0.25) < 0.01
    window.preview.speed.setCurrentIndex(3)
    assert player.playbackRate() == 2.0
    qtbot.mouseClick(window.preview.stop, Qt.MouseButton.LeftButton)
    assert player.playbackState() == QMediaPlayer.PlaybackState.StoppedState
    assert player.position() == 0
    assert window.errors.toPlainText() == ""
    window.close()


def test_import_errors_recovery_audio_image(qtbot, media_files, tmp_path):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    broken = tmp_path / "corrupt.mp4"
    broken.write_text("invalid")
    window.import_paths([broken])
    qtbot.waitUntil(lambda: window.worker is None, timeout=30000)
    assert "corrupt.mp4" in window.errors.toPlainText()
    window.import_paths([media_files["audio"], media_files["image"]])
    qtbot.waitUntil(lambda: window.worker is None and len(window.media) == 2, timeout=30000)
    for index in range(2):
        item = window.library.topLevelItem(index)
        window.library.setCurrentItem(item)
        if item.text(0).endswith(".png"):
            assert not window.preview.image.isNull()
            assert not window.preview.play.isEnabled()
        else:
            window.preview.toggle()
            qtbot.waitUntil(lambda: window.preview.player.position() > 200, timeout=10000)
            window.preview.player.stop()
    window.close()


def test_native_picker_connected(qtbot, media_files, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(
        QFileDialog, "getOpenFileNames", lambda *args: ([str(media_files["video"])], "Media")
    )
    window.import_action.trigger()
    qtbot.waitUntil(lambda: len(window.media) == 1 and window.worker is None, timeout=30000)
    assert window.preview.player.source() == QUrl.fromLocalFile(str(media_files["video"]))
    window.close()


def test_close_during_import(qtbot, media_files):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.import_paths(list(media_files.values()))
    window.close()
    qtbot.waitUntil(lambda: window.worker is None and not window.isVisible(), timeout=30000)


def test_drop_import_and_reject_remote(qtbot, media_files):
    from PySide6.QtWidgets import QApplication

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(media_files["video"]))])
    enter = QDragEnterEvent(
        QPoint(50, 50),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(window, enter)
    assert enter.isAccepted()
    drop = QDropEvent(
        QPointF(50, 50),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(window, drop)
    assert drop.isAccepted()
    qtbot.waitUntil(lambda: len(window.media) == 1 and window.worker is None, timeout=30000)
    mime.setUrls([QUrl("https://example.invalid/video.mp4")])
    remote = QDragEnterEvent(
        QPoint(50, 50),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(window, remote)
    assert not remote.isAccepted()
    window.close()


def test_cancel_import_preserves_responsive_window(qtbot, media_files):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.import_paths(list(media_files.values()))
    window.cancel_action.trigger()
    qtbot.waitUntil(lambda: window.worker is None, timeout=30000)
    assert len(window.media) <= 1
    assert not window.cancel_action.isEnabled()
    window.import_paths([media_files["video"]])
    qtbot.waitUntil(
        lambda: media_files["video"] in window.media and window.worker is None, timeout=30000
    )
    window.close()
