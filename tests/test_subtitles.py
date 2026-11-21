"""Subtitle editing, migration, interchange and real burned-frame verification."""

import subprocess
from dataclasses import replace

import pytest

from app.core.command_manager import ProjectSession
from app.core.project_manager import decode, encode, load_project, save_project
from app.core.project_schema import Project, validate
from app.core.render_engine import render_project
from app.core.subtitles import Subtitle, SubtitleEngine, SubtitleStyle, export_text, parse_text
from app.export.ffmpeg_builder import ExportSettings
from app.utils.paths import find_tool


def test_edit_split_merge_undo_and_reopen(tmp_path):
    session = ProjectSession()
    engine = SubtitleEngine(session)
    identifier = engine.add(100, 2000, "Hello world")
    engine.split(identifier, 1000)
    assert [(s.start_ms, s.end_ms) for s in session.project.subtitles] == [
        (100, 1000),
        (1000, 2000),
    ]
    engine.merge(identifier)
    assert session.project.subtitles[0].text == "Hello world Hello world"
    session.undo()
    assert len(session.project.subtitles) == 2
    session.redo()
    engine.edit(identifier, 300, 2500, "Edited\nUnicode اردو")
    style = SubtitleStyle(size=60, color="#FFFF00")
    engine.update(session.project.subtitles, subtitle_style=style, transcription='{"device":"cpu"}')
    path = tmp_path / "subtitled.astra"
    save_project(session.project, path)
    assert load_project(path) == session.project
    assert session.project.end == 75
    engine.delete(identifier)
    assert not session.project.subtitles
    session.undo()
    assert session.project.subtitles[0].end_ms == 2500


@pytest.mark.parametrize("kind", ["srt", "vtt"])
def test_subtitle_interchange(kind):
    subtitles = (Subtitle("a", 123, 4567, "Hello\nWorld"), Subtitle("b", 9000, 10000, "Second"))
    text = export_text(subtitles, kind)
    restored = parse_text(text, kind)
    assert [(s.start_ms, s.end_ms, s.text) for s in restored] == [
        (s.start_ms, s.end_ms, s.text) for s in subtitles
    ]
    with pytest.raises(ValueError):
        parse_text("1\n00:00:05,000 --> 00:00:02,000\nBad\n", kind)


def test_invalid_subtitles_and_legacy_migration(tmp_path):
    for segment in (
        Subtitle("a", -1, 100, "x"),
        Subtitle("a", 100, 100, "x"),
        Subtitle("a", 0, 100, ""),
    ):
        with pytest.raises(ValueError):
            validate(Project(subtitles=(segment,)))
    with pytest.raises(ValueError):
        validate(Project(subtitle_style=SubtitleStyle(color="red;movie=bad")))
    data = encode(Project(), tmp_path)
    data["schema_version"] = 2
    for key in ("subtitles", "subtitle_style", "transcription", "audio_master"):
        data.pop(key)
    for track in data["tracks"]:
        track.pop("audio")
    assert decode(data, tmp_path).subtitles == ()
    data["schema_version"] = 999
    with pytest.raises(ValueError):
        decode(data, tmp_path)


def test_ass_escaping_and_burned_frames(tmp_path):
    folder = tmp_path / "subtitles ü space"
    folder.mkdir()
    project = Project(
        width=320,
        height=180,
        subtitles=(Subtitle("a", 500, 1500, "Astra captions"),),
        subtitle_style=SubtitleStyle(size=28, bottom_margin=20),
    )
    escaped = export_text((Subtitle("x", 0, 1000, r"{\pos(0,0)}literal"),), "ass")
    assert r"{\pos" not in escaped
    plain, burned = folder / "plain.mp4", folder / "burned.mp4"
    render_project(project, ExportSettings(320, 180), plain)
    render_project(project, ExportSettings(320, 180, 20, True), burned)

    def pixels(path, position):
        return subprocess.run(
            [
                find_tool("ffmpeg"),
                "-v",
                "error",
                "-i",
                str(path),
                "-ss",
                str(position),
                "-frames:v",
                "1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "gray",
                "pipe:1",
            ],
            check=True,
            capture_output=True,
            timeout=30,
        ).stdout

    assert max(pixels(plain, 0.8)) < 5
    assert max(pixels(burned, 0.1)) < 5
    assert sum(value > 180 for value in pixels(burned, 0.8)) > 100
    assert len(pixels(burned, 0.8)) == 320 * 180


def test_style_changes_are_reversible():
    session = ProjectSession()
    engine = SubtitleEngine(session)
    engine.update(
        (), subtitle_style=replace(session.project.subtitle_style, font="Verdana", size=70)
    )
    session.undo()
    assert session.project.subtitle_style == SubtitleStyle()
