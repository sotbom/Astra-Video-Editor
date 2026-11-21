"""Real voice DSP output: frequency, timing, formant modes and project compatibility."""

import math
import subprocess
from dataclasses import replace

import pytest
from test_audio import output, pcm, rms

from app.audio.effects import AudioSettings
from app.audio.voice import VOICE_FIELDS
from app.core.command_manager import ProjectSession
from app.core.media_probe import probe_media
from app.core.project_manager import decode, encode, load_project, save_project
from app.core.render_engine import render_project
from app.core.timeline_engine import TimelineEngine
from app.export.ffmpeg_builder import ExportSettings
from app.utils.paths import find_tool


@pytest.fixture
def voice_edit(media_files):
    session = ProjectSession()
    engine = TimelineEngine(session)
    media = engine.import_media(probe_media(media_files["audio"]))
    clip = engine.add_clip(media, session.project.tracks[1].id, 30)
    return session, engine, clip


def frequency(values, start=1.3, end=2.3):
    samples = values[round(start * 48000) * 2 : round(end * 48000) * 2 : 2]
    crossings = sum(a <= 0 < b for a, b in zip(samples, samples[1:]))
    return crossings / (end - start)


@pytest.mark.parametrize("pitch,tempo", [(7, 1), (-5, 1), (0, 2), (0, 0.5)])
def test_pitch_tempo_duration_and_timeline_slot(voice_edit, tmp_path, pitch, tempo):
    session, engine, clip_id = voice_edit
    clip = session.project.clip_by_id(clip_id)
    engine.set_audio(
        clip.track_id,
        AudioSettings(voice=True, pitch_semitones=pitch, tempo=tempo, preserve_formants=False),
    )
    path = output(session.project, tmp_path)
    values = pcm(path)
    assert len(values) == 4 * 48000 * 2
    assert probe_media(path).duration_ms == 4000
    assert rms(values, 0.2, 0.8) < 0.00001  # delay survives DSP
    assert abs(frequency(values) - 660 * 2 ** (pitch / 12)) < 4
    assert rms(values, 1.5, 2) > 0.02
    if tempo == 2:
        assert rms(values, 3, 3.8) < 0.00001  # faster audio is padded inside slot
    else:
        assert rms(values, 3, 3.8) > 0.02


def test_formant_modes_timbre_and_bypass(voice_edit, tmp_path):
    session, engine, _ = voice_edit
    track = session.project.tracks[1].id
    base = pcm(output(session.project, tmp_path, "base.wav"))
    settings = AudioSettings(voice=True, pitch_semitones=4, preserve_formants=True)
    engine.set_audio(track, settings)
    preserved = pcm(output(session.project, tmp_path, "preserved.wav"))
    engine.set_audio(track, replace(settings, preserve_formants=False))
    shifted = pcm(output(session.project, tmp_path, "shifted.wav"))
    assert all(math.isfinite(v) for v in preserved)
    assert abs(frequency(shifted) - frequency(preserved)) < 2
    assert sum(abs(a - b) for a, b in zip(preserved, shifted)) / len(shifted) > 0.0001
    engine.set_audio(track, replace(settings, voice=False, tempo=2, timbre_db=6))
    assert pcm(output(session.project, tmp_path, "bypass.wav")) == base


def test_timbre_shelf_changes_high_frequency_energy(tmp_path):
    source = tmp_path / "high.wav"
    subprocess.run(
        [
            find_tool("ffmpeg"),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=6000:sample_rate=48000:duration=3",
            str(source),
        ],
        check=True,
        timeout=30,
    )
    session = ProjectSession()
    engine = TimelineEngine(session)
    media = engine.import_media(probe_media(source))
    track = session.project.tracks[1].id
    engine.add_clip(media, track, 0)
    base = pcm(output(session.project, tmp_path, "base.wav"))
    engine.set_audio(track, AudioSettings(voice=True, timbre_db=6))
    bright = pcm(output(session.project, tmp_path, "bright.wav"))
    assert rms(bright, 1, 2) > rms(base, 1, 2) * 1.5


def test_voice_persistence_migration_undo_and_validation(voice_edit, tmp_path):
    session, engine, _ = voice_edit
    original = session.project
    settings = AudioSettings(voice=True, pitch_semitones=-3, tempo=1.1, timbre_db=-1)
    engine.set_audio(original.tracks[1].id, settings)
    path = tmp_path / "voice.astra"
    save_project(session.project, path)
    assert load_project(path) == session.project
    session.undo()
    assert session.project == original
    session.redo()
    assert session.project.tracks[1].audio == settings
    old = encode(original, tmp_path)
    old["schema_version"] = 4
    for track in old["tracks"]:
        for key in VOICE_FIELDS:
            track["audio"].pop(key)
    assert decode(old, tmp_path) == original
    for bad in (
        replace(settings, pitch_semitones=float("nan")),
        replace(settings, tempo=0),
        replace(settings, preserve_formants=1),
    ):
        with pytest.raises(ValueError):
            engine.set_audio(original.tracks[1].id, bad)
    assert session.project.tracks[1].audio == settings


def test_missing_voice_backend_preserves_output(voice_edit, tmp_path, monkeypatch):
    from app.audio import voice

    session, engine, _ = voice_edit
    engine.set_audio(session.project.tracks[1].id, AudioSettings(voice=True, pitch_semitones=2))
    monkeypatch.setattr(voice, "_rubberband_available", lambda *args: False)
    destination = tmp_path / "existing.wav"
    destination.write_bytes(b"existing output")
    with pytest.raises(ValueError, match="librubberband"):
        render_project(
            session.project, ExportSettings(audio_only=True), destination, overwrite=True
        )
    assert destination.read_bytes() == b"existing output"
    engine.set_audio(session.project.tracks[1].id, AudioSettings())
    assert output(session.project, tmp_path).is_file()  # ordinary mixing still works


def test_voice_processing_reaches_mp4_export(voice_edit, tmp_path):
    session, engine, _ = voice_edit
    engine.set_audio(
        session.project.tracks[1].id,
        AudioSettings(voice=True, pitch_semitones=-3, preserve_formants=False),
    )
    destination = tmp_path / "voice.mp4"
    render_project(session.project, ExportSettings(width=320, height=180), destination)
    info = probe_media(destination)
    assert info.video_codec == "h264" and info.audio_codec == "aac"
    assert abs(frequency(pcm(destination)) - 660 * 2 ** (-3 / 12)) < 4
