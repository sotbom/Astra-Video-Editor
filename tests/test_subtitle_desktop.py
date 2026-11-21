"""Connected subtitle controls and actual optional transcription integration."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog

from app.ai.model_manager import installed
from app.core.media_probe import probe_media
from app.core.project_manager import load_project, save_project
from app.core.subtitles import parse_text
from app.ui.main_window import MainWindow
from app.ui.subtitle_panel import SubtitlePanel
from app.utils.paths import ROOT


def test_subtitle_edit_preview_import_export_and_undo(qtbot, tmp_path, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)
    panel = SubtitlePanel(window)
    qtbot.addWidget(panel)
    panel.show()
    panel.start.setValue(500)
    panel.end.setValue(2500)
    panel.text.setPlainText("Hello Astra")
    qtbot.mouseClick(panel.edit_buttons[0], Qt.MouseButton.LeftButton)
    assert panel.table.rowCount() == 1
    panel.table.selectRow(0)
    panel.text.setPlainText("Edited Astra")
    qtbot.mouseClick(panel.edit_buttons[1], Qt.MouseButton.LeftButton)
    window.timeline_preview.engine.seek(30)
    assert window.timeline_preview.caption.text() == "Edited Astra"
    window.timeline_preview.engine.seek(0)
    assert window.timeline_preview.caption.text() == ""
    panel.find.setText("Astra")
    panel.replacement.setText("subtitles")
    panel.replace_all()
    assert window.session.project.subtitles[0].text == "Edited subtitles"
    window.session.undo()
    assert window.session.project.subtitles[0].text == "Edited Astra"
    for extension in ("srt", "vtt", "ass"):
        destination = tmp_path / f"captions.{extension}"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, p=destination: (str(p), ""))
        panel.export_file()
        content = destination.read_text(encoding="utf-8")
        assert "Edited Astra" in content
        if extension != "ass":
            assert parse_text(content, extension)[0].start_ms == 500
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *a: (str(tmp_path / "captions.srt"), "")
    )
    panel.import_file()
    assert len(window.session.project.subtitles) == 2
    panel.reject()
    window.close()


def test_transcribe_selected_clip_to_persisted_subtitles(qtbot, tmp_path):
    speech = ROOT / "tests/fixtures/generated/speech.wav"
    if not installed("tiny.en") or not speech.exists():
        pytest.skip("Optional AI model and generated speech fixture required")
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    media = window.engine.import_media(probe_media(speech))
    clip = window.engine.add_clip(media, window.session.project.tracks[1].id, 30)
    window.timeline.select_clip(clip)
    panel = SubtitlePanel(window)
    qtbot.addWidget(panel)
    panel.show()
    panel.language.setText("en")
    qtbot.mouseClick(panel.transcribe, Qt.MouseButton.LeftButton)
    assert panel.worker is not None
    assert not panel.table.isEnabled()
    qtbot.waitUntil(lambda: panel.worker is None, timeout=60000)
    assert "Added" in panel.status.text(), panel.status.text()
    project = window.session.project
    assert len(project.subtitles) >= 1
    assert min(s.start_ms for s in project.subtitles) >= 1000
    assert "cpu" in project.transcription
    path = tmp_path / "transcribed.astra"
    save_project(project, path)
    reopened = load_project(path)
    assert reopened.subtitles == project.subtitles
    assert panel.table.rowCount() == len(project.subtitles)
    window.session.undo()
    assert not window.session.project.subtitles
    panel.reject()
    window.close()


def test_missing_model_and_worker_failure_preserve_project(
    qtbot, media_files, tmp_path, monkeypatch
):
    window = MainWindow()
    qtbot.addWidget(window)
    media = window.engine.import_media(probe_media(media_files["video"]))
    clip = window.engine.add_clip(media, window.session.project.tracks[0].id, 0)
    window.timeline.select_clip(clip)
    panel = SubtitlePanel(window)
    qtbot.addWidget(panel)
    before = window.session.project
    monkeypatch.setenv("ASTRA_MODELS_DIR", str(tmp_path))
    panel.perform(panel.transcribe_clip)
    assert "Download" in panel.status.text()
    monkeypatch.setenv("ASTRA_AI_PYTHON", str(tmp_path / "missing.exe"))
    panel.download_model()
    qtbot.waitUntil(lambda: panel.worker is None, timeout=10000)
    assert "environment missing" in panel.status.text()
    assert window.session.project == before
    panel.reject()
    window.close()
