import json
from dataclasses import replace
from fractions import Fraction

import pytest

from app.core.command_manager import ProjectSession
from app.core.media_probe import probe_media
from app.core.project_manager import decode, encode, load_project, save_project
from app.core.project_schema import Project, validate
from app.core.timeline_engine import TimelineEngine


@pytest.fixture
def edit(media_files):
    session = ProjectSession()
    engine = TimelineEngine(session)
    media_id = engine.import_media(probe_media(media_files["video"]))
    clip_id = engine.add_clip(media_id, session.project.tracks[0].id, 0)
    return session, engine, clip_id


def test_split_trim_move_undo_redo(edit):
    session, engine, clip_id = edit
    original = session.project
    right_id = engine.split(clip_id, 60)
    assert session.project.clip_by_id(clip_id).source_out == 60
    assert session.project.clip_by_id(right_id).source_in == 60
    engine.edit_clip(right_id, start=90, source_in=75, source_out=150)
    clip = session.project.clip_by_id(right_id)
    assert (clip.start, clip.duration, clip.end) == (90, 75, 165)
    edited = session.project
    session.undo()
    session.undo()
    assert session.project == original
    session.redo()
    session.redo()
    assert session.project == edited
    engine.delete(right_id)
    assert len(session.project.clips) == 1
    session.undo()
    assert session.project == edited


def test_rejected_edits_are_atomic_and_tracks_lock(edit):
    session, engine, clip_id = edit
    original = session.project
    with pytest.raises(ValueError):
        engine.edit_clip(clip_id, start=-1, source_in=0, source_out=180)
    with pytest.raises(ValueError):
        engine.edit_clip(clip_id, start=0, source_in=0, source_out=181)
    with pytest.raises(ValueError):
        engine.split(clip_id, 0)
    with pytest.raises(ValueError, match="overlap"):
        engine.add_clip(original.media[0].id, original.tracks[0].id, 60)
    assert session.project == original
    second = engine.add_track("video")
    engine.edit_clip(clip_id, start=30, source_in=0, source_out=180, track_id=second)
    engine.set_track(second, locked=True)
    with pytest.raises(ValueError, match="Unlock"):
        engine.delete(clip_id)


def test_roundtrip_backup_relative_paths_and_dirty(edit, tmp_path):
    session, engine, clip_id = edit
    path = tmp_path / "project.astra"
    save_project(session.project, path)
    assert load_project(path) == session.project
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert not raw["media"][0]["info"]["path"].startswith("C:")
    original = session.project
    session.mark_saved(original)
    assert not session.dirty
    engine.split(clip_id, 60)
    save_project(session.project, path)
    assert load_project(path.with_suffix(".astra.bak")) == original
    assert load_project(path) == session.project
    session.undo()
    assert not session.dirty
    session.redo()
    assert session.dirty


def test_atomic_failure_preserves_file(edit, tmp_path, monkeypatch):
    import app.core.project_manager as persistence

    session, engine, clip_id = edit
    path = tmp_path / "safe.astra"
    save_project(session.project, path)
    before = path.read_bytes()
    engine.split(clip_id, 90)

    def fail_replace(*args):
        raise OSError("disk unavailable")

    monkeypatch.setattr(persistence.os, "replace", fail_replace)
    with pytest.raises(OSError):
        save_project(session.project, path, backup=False)
    assert path.read_bytes() == before
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(schema_version=999),
        lambda d: d["clips"][0].update(source_in=-1),
        lambda d: d["clips"][0].update(media_id="missing"),
        lambda d: d["project"].update(fps_den=0),
        lambda d: d["project"].update(fps_num=True),
        lambda d: d["media"][0]["info"].update(path="https://example.com/a.mp4"),
    ],
)
def test_invalid_project_rejected(edit, tmp_path, mutation):
    data = encode(edit[0].project, tmp_path)
    mutation(data)
    with pytest.raises(ValueError):
        decode(data, tmp_path)


def test_rational_timing_and_missing_media(edit, tmp_path):
    project = Project(fps_num=30000, fps_den=1001)
    assert project.fps == Fraction(30000, 1001)
    assert project.milliseconds(30000) == 1001000
    assert project.frames(1001000) == 30000
    session, engine, _ = edit
    source = session.project.media[0]
    missing = replace(source, info=replace(source.info, path=tmp_path / "gone.mp4"))
    project = replace(session.project, media=(missing,))
    validate(project)
    assert project.missing_media() == [missing]
    session.reset(project)
    engine.relink(source.id, source.info)
    assert not session.project.missing_media()


def test_source_overwrite_prevented(edit):
    project = edit[0].project
    with pytest.raises(ValueError, match="source media"):
        save_project(project, project.media[0].info.path)
