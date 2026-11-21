"""Connected Audio Studio processing, cached timeline peaks and playable output."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog

from app.audio.effects import AudioSettings
from app.core.media_probe import probe_media
from app.ui.audio_panel import AudioPanel
from app.ui.main_window import MainWindow


def test_audio_studio_waveforms_process_play_analyze_export(
    qtbot, media_files, tmp_path, monkeypatch
):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    media = window.engine.import_media(probe_media(media_files["audio"]))
    clip = window.engine.add_clip(media, window.session.project.tracks[1].id, 0)
    window.timeline.select_clip(clip)
    panel = AudioPanel(window)
    qtbot.addWidget(panel)
    panel.show()
    panel.controls["gain_db"].setValue(-6)
    panel.controls["pan"].setValue(-1)
    panel.fade_in.setValue(250)
    qtbot.mouseClick(panel.apply_button, Qt.MouseButton.LeftButton)
    assert window.session.project.tracks[1].audio.gain_db == -6
    assert window.session.project.clips[0].fade_in_ms == 250
    window.session.undo()
    assert window.session.project.tracks[1].audio == AudioSettings()
    window.session.redo()
    qtbot.mouseClick(panel.wave, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: panel.wave_worker is None, timeout=15000)
    assert media_files["audio"] in window.timeline.view.waveforms
    qtbot.mouseClick(panel.after, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: panel.worker is None, timeout=15000)
    assert panel.preview_path.is_file()
    assert panel.progress.value() == 100
    panel.preview.toggle()
    qtbot.waitUntil(lambda: panel.preview.player.position() > 200, timeout=10000)
    panel.preview.player.stop()
    qtbot.mouseClick(panel.analyze, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: panel.analysis_worker is None, timeout=15000)
    assert "LUFS" in panel.status.text()
    destination = tmp_path / "studio.wav"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a: (str(destination), ""))
    panel.export_wav()
    qtbot.waitUntil(lambda: panel.worker is None, timeout=15000)
    assert probe_media(destination).sample_rate == 48000
    panel.reject()
    window.close()


def test_audio_studio_invalid_controls_and_running_cancel(qtbot, media_files):
    window = MainWindow()
    qtbot.addWidget(window)
    media = window.engine.import_media(probe_media(media_files["image"]))
    clip = window.engine.add_clip(media, window.session.project.tracks[0].id, 0)
    window.engine.edit_clip(clip, start=0, source_in=0, source_out=1800000)
    window.timeline.select_clip(clip)
    panel = AudioPanel(window)
    qtbot.addWidget(panel)
    panel.show()
    panel.controls["highpass"].setValue(2000)
    panel.controls["lowpass"].setValue(2000)
    before = window.session.project
    panel.apply()
    assert "below" in panel.status.text()
    assert window.session.project == before
    panel.render()
    qtbot.waitUntil(
        lambda: bool(list(Path(panel.temp.name).glob(".astra-render-*"))),
        timeout=10000,
    )
    panel.reject()
    qtbot.waitUntil(lambda: panel.worker is None, timeout=15000)
    assert panel.isVisible()
    assert "cancelled" in panel.status.text()
    assert panel.preview_path is None
    panel.reject()
    window.close()
