"""Verify voice controls, real previews, comparison invalidation and persistence."""

from pathlib import Path

from PySide6.QtCore import Qt

from app.core.media_probe import probe_media
from app.core.project_manager import load_project, save_project
from app.ui.audio_panel import AudioPanel
from app.ui.main_window import MainWindow


def test_voice_presets_comparison_play_and_reopen(qtbot, media_files, tmp_path):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    media = window.engine.import_media(probe_media(media_files["audio"]))
    clip = window.engine.add_clip(media, window.session.project.tracks[1].id, 0)
    window.timeline.select_clip(clip)
    panel = AudioPanel(window)
    qtbot.addWidget(panel)
    panel.show()
    panel.controls["gain_db"].setValue(-2)
    panel.voice_preset.setCurrentText("Natural lower")
    qtbot.mouseClick(panel.load_voice, Qt.MouseButton.LeftButton)
    assert panel.controls["gain_db"].value() == -2
    qtbot.mouseClick(panel.apply_button, Qt.MouseButton.LeftButton)
    assert window.session.project.tracks[1].audio.pitch_semitones == -3
    for button in (panel.before, panel.after):
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: panel.worker is None, timeout=15000)
        assert panel.preview_path.is_file()
    assert len(panel.comparisons) == 2
    before = panel.comparisons[True].path
    after = panel.comparisons[False].path
    assert before.read_bytes() != after.read_bytes()
    for button, path in ((panel.listen_before, before), (panel.listen_after, after)):
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
        assert Path(panel.preview.player.source().toLocalFile()) == path
        panel.preview.toggle()
        qtbot.waitUntil(lambda: panel.preview.player.position() > 200, timeout=10000)
        panel.preview.player.stop()
    destination = tmp_path / "voice.astra"
    save_project(window.session.project, destination)
    assert load_project(destination) == window.session.project
    window.session.undo()
    assert not panel.comparisons and panel.preview_path is None
    assert not panel.listen_after.isEnabled()
    window.session.redo()
    assert panel.controls["pitch_semitones"].value() == -3
    panel.reject()
    assert not after.exists() and not before.exists()
    window.close()
